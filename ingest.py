# ingest.py: load PDFs, tag each page with type and year, chunk, embed and store in Chroma.
# Usage: uv run python ingest.py          (pilot set)
#        uv run python ingest.py --full   (whole corpus)
import csv
import logging
import sys
from pathlib import Path

import chromadb
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers.file.base import default_file_metadata_func
from llama_index.vector_stores.chroma import ChromaVectorStore

import config

logging.getLogger("pypdf").setLevel(logging.ERROR)  # hide warnings about damaged-but-readable files

INVENTORY = "inventory.csv"
EMBED_KEYS = {"doc_type", "year"}                            # the only metadata the embedding sees
LLM_KEYS = {"file_name", "doc_type", "year", "page_label"}   # what the LLM sees, for citations
UNKNOWN = {"doc_type": "unknown", "year": ""}                # for files missing from inventory.csv


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

    reader = SimpleDirectoryReader(input_dir=input_dir, required_exts=[".pdf"], file_metadata=file_metadata)
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


def build_index(docs):
    """Chunk the pages, embed them and store them in a fresh Chroma collection."""
    nodes = SentenceSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP) \
        .get_nodes_from_documents(docs, show_progress=True)

    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    try:  # start fresh; list_collections() changes shape between Chroma versions, so just try
        client.delete_collection(config.COLLECTION)
    except Exception:
        pass  # collection didn't exist yet
    collection = client.create_collection(config.COLLECTION)

    storage = StorageContext.from_defaults(vector_store=ChromaVectorStore(chroma_collection=collection))
    index = VectorStoreIndex(nodes, storage_context=storage, show_progress=True)
    return index, nodes, collection


if __name__ == "__main__":
    config.configure()  # sets MiniLM as Settings.embed_model
    input_dir = config.CORPUS_DIR if "--full" in sys.argv else config.PILOT_DIR

    docs = load_documents(input_dir)
    index, nodes, collection = build_index(docs)

    print(f"\nPages:      {len(docs)}")
    print(f"Chunks:     {len(nodes)}")
    print(f"Collection: {collection.count()}  ({'matches' if collection.count() == len(nodes) else 'MISMATCH'})")
    unknown = sum(1 for d in docs if d.metadata["doc_type"] == UNKNOWN["doc_type"])
    print(f"Unknown:    {unknown} pages not matched in {INVENTORY}")
    print("What the embedding sees:\n ", nodes[0].get_metadata_str(mode="embed"))
    print("What the LLM sees:\n ", nodes[0].get_metadata_str(mode="llm"))

    question = "How much was allocated to health in FY 2022/23?"
    print(f"\nTest query: {question}")
    for n in index.as_retriever(similarity_top_k=config.TOP_K).retrieve(question):
        m = n.node.metadata
        print(f"  {n.score:.3f}  {m['doc_type']:<22} {m['year']:<9} p.{m.get('page_label', '?'):<5} {m['file_name'][:60]}")
