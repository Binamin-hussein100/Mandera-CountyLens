# ingest.py: load PDFs, tag each page with type and year, chunk, embed and store in Chroma.
# Re-runs only chunk and embed pages that are new or changed (tracked in a docstore).
# Usage: uv run python ingest.py                (pilot set  -> collection "mandera_pilot")
#        uv run python ingest.py --full         (corpus/    -> collection "mandera")
#        add --rebuild to start from scratch (needed after changing chunk size or embedding model)
import csv
import logging
import sys
import time
from pathlib import Path

import chromadb
from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.ingestion import DocstoreStrategy, IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers.file.base import default_file_metadata_func
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.vector_stores.chroma import ChromaVectorStore

import config

logging.getLogger("pypdf").setLevel(logging.ERROR)  # hide warnings about damaged-but-readable files

INVENTORY = "inventory.csv"
EMBED_KEYS = {"doc_type", "year"}                            # the only metadata the embedding sees
LLM_KEYS = {"file_name", "doc_type", "year", "page_label"}   # what the LLM sees, for citations
UNKNOWN = {"doc_type": "unknown", "year": ""}                # for files missing from inventory.csv
PILOT_COLLECTION = f"{config.COLLECTION}_pilot"
CHROMA_BATCH = 5000  # Chroma refuses more than ~5,400 chunks in one add


class BatchedChromaVectorStore(ChromaVectorStore):
    """ChromaVectorStore that adds chunks in batches. The pipeline sends all new chunks in a
    single call, which Chroma rejects for large builds."""

    def add(self, nodes, **kwargs):
        ids = []
        for i in range(0, len(nodes), CHROMA_BATCH):
            ids += super().add(nodes[i:i + CHROMA_BATCH], **kwargs)
        return ids


def load_inventory(path=INVENTORY):
    """Read inventory.csv into {file name: {"doc_type": ..., "year": ...}}."""
    with open(path, encoding="utf-8") as f:
        return {Path(r["file"]).name: {"doc_type": r["doc_type"], "year": r["year"]}
                for r in csv.DictReader(f)}


def load_documents(input_dir=config.PILOT_DIR):
    """Load every PDF in input_dir as one Document per page, tagged with doc_type and year."""
    inventory = load_inventory()

    def file_metadata(file_path):
        # A custom function replaces the reader's default metadata, so start from the default
        # (file_name, file_path, size, dates) and add the inventory fields on top.
        meta = default_file_metadata_func(file_path)
        meta.update(inventory.get(Path(file_path).name, UNKNOWN))
        return meta

    # filename_as_id gives each page a stable id (file path + page number), so the docstore
    # can recognise the same page on the next run.
    reader = SimpleDirectoryReader(input_dir=input_dir, required_exts=[".pdf"],
                                   file_metadata=file_metadata, filename_as_id=True)
    docs = reader.load_data(show_progress=True)

    # Metadata counts against the chunk size, so hide everything the model doesn't need
    # (the reader leaves the full file_path visible to the LLM by default).
    for doc in docs:
        doc.excluded_embed_metadata_keys = [k for k in doc.metadata if k not in EMBED_KEYS]
        doc.excluded_llm_metadata_keys = [k for k in doc.metadata if k not in LLM_KEYS]

    missing = {d.metadata["file_name"] for d in docs if d.metadata["doc_type"] == UNKNOWN["doc_type"]}
    if missing:
        print(f"Warning: {len(missing)} PDFs not in {INVENTORY}, tagged unknown: {sorted(missing)[:5]}")
    return docs


def build_index(docs, collection_name, rebuild=False):
    """Chunk and embed new or changed pages and store them in Chroma.

    The docstore remembers a fingerprint (text + metadata) of every page already stored.
    Unchanged pages are skipped, changed ones are replaced, and pages whose PDF was removed
    are deleted from Chroma too.
    """
    docstore_path = Path(config.CHROMA_DIR) / f"{collection_name}_docstore.json"
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)

    # Without a docstore we can't tell what the collection holds, so start it fresh.
    if rebuild or not docstore_path.exists():
        try:  # list_collections() changes shape between Chroma versions, so just try
            client.delete_collection(collection_name)
        except Exception:
            pass  # collection didn't exist yet
        docstore_path.unlink(missing_ok=True)

    docstore = SimpleDocumentStore.from_persist_path(str(docstore_path)) if docstore_path.exists() \
        else SimpleDocumentStore()
    collection = client.get_or_create_collection(collection_name)
    vector_store = BatchedChromaVectorStore(chroma_collection=collection)

    pipeline = IngestionPipeline(
        transformations=[
            SentenceSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP),
            Settings.embed_model,
        ],
        docstore=docstore,
        vector_store=vector_store,
        docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE,
    )
    nodes = pipeline.run(documents=docs, show_progress=True)  # only the new or changed chunks
    pipeline.docstore.persist(str(docstore_path))

    index = VectorStoreIndex.from_vector_store(vector_store)
    return index, nodes, collection


if __name__ == "__main__":
    config.configure()  # sets MiniLM as Settings.embed_model
    full = "--full" in sys.argv
    input_dir = config.CORPUS_DIR if full else config.PILOT_DIR
    collection_name = config.COLLECTION if full else PILOT_COLLECTION

    t0 = time.perf_counter()
    docs = load_documents(input_dir)
    t1 = time.perf_counter()
    index, nodes, collection = build_index(docs, collection_name, rebuild="--rebuild" in sys.argv)
    t2 = time.perf_counter()

    print(f"\nCollection: {collection_name}")
    print(f"PDFs read:             {len({d.metadata['file_name'] for d in docs})}")
    print(f"Pages read:            {len(docs)}")
    print(f"Time to read PDFs:     {t1 - t0:.0f} s")
    print(f"Time to chunk+embed+store: {t2 - t1:.0f} s")
    print(f"Total time:            {t2 - t0:.0f} s")
    print(f"Chunks added/updated:  {len(nodes)}  (0 = nothing changed since the last run)")
    print(f"Chunks in collection:  {collection.count()}")
    unknown = sum(1 for d in docs if d.metadata["doc_type"] == UNKNOWN["doc_type"])
    print(f"Unknown:               {unknown} pages not matched in {INVENTORY}")
    if nodes:
        print("What the embedding sees:\n ", nodes[0].get_metadata_str(mode="embed"))
        print("What the LLM sees:\n ", nodes[0].get_metadata_str(mode="llm"))

    question = "How much was allocated to health in FY 2022/23?"
    print(f"\nTest query: {question}")
    for n in index.as_retriever(similarity_top_k=config.TOP_K).retrieve(question):
        m = n.node.metadata
        print(f"  {n.score:.3f}  {m['doc_type']:<22} {m['year']:<9} p.{m.get('page_label', '?'):<5} {m['file_name'][:60]}")
