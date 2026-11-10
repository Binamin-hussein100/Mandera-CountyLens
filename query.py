# query.py: answer a question from the Chroma index, with page-level citations.
# Usage: uv run python query.py "How much was allocated to health in FY 2022/23?"
#        uv run python query.py --pilot "..."   (ask the 50-PDF pilot index instead)
import re
import sys

import chromadb
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.llms import ChatMessage
from llama_index.core.schema import MetadataMode
from llama_index.vector_stores.chroma import ChromaVectorStore

import config

# Short names for citation labels, e.g. "FY 2023/24 Budget".
TYPE_NAMES = {
    "budget": "Budget",
    "budget_implementation": "Budget Implementation Report",
    "adp": "ADP",
    "cidp": "CIDP",
    "fiscal_strategy": "Fiscal Strategy Paper",
    "cbrop": "CBROP",
    "revenue": "Revenue Document",
    "audit": "Audit Report",
    "progress_report": "Progress Report",
    "law_policy": "Act/Policy",
    "plan_other": "Plan",
    "drought_bulletin": "Drought Bulletin",
    "humanitarian": "Humanitarian Report",
    "research": "Research Paper",
}


def open_index(collection=config.COLLECTION):
    """Open an existing Chroma collection built by ingest.py (no re-embedding).
    "mandera" is the full corpus, "mandera_pilot" the 50-PDF pilot."""
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    store = ChromaVectorStore(chroma_collection=client.get_collection(collection))
    return VectorStoreIndex.from_vector_store(store)


def label(i, meta):
    """Citation label for source i, e.g. "Source 1: FY 2023/24 Budget | p. 12"."""
    year = meta.get("year", "")
    year = f"FY {year}" if "/" in year else year
    name = TYPE_NAMES.get(meta.get("doc_type"), "Document")
    return f"Source {i}: {f'{year} ' if year else ''}{name} | p. {meta.get('page_label', '?')}"


def answer(question, index, top_k=config.TOP_K):
    """Retrieve top_k chunks, ask the LLM, and return (answer text, list of sources)."""
    hits = index.as_retriever(similarity_top_k=top_k).retrieve(question)
    sources, blocks = [], []
    for i, hit in enumerate(hits, 1):
        meta = hit.node.metadata
        sources.append({"n": i, "label": label(i, meta), "file": meta["file_name"],
                        "page": str(meta.get("page_label", "")), "score": hit.score})
        text = hit.node.get_content(metadata_mode=MetadataMode.NONE)
        blocks.append(f"[{label(i, meta)}]\nFile: {meta['file_name']}\n{text}")

    user = "Excerpts:\n\n" + "\n\n---\n\n".join(blocks) + f"\n\nQuestion: {question}"
    reply = Settings.llm.chat([ChatMessage(role="system", content=config.SYSTEM_PROMPT),
                               ChatMessage(role="user", content=user)])
    return reply.message.content, sources


def cited(text):
    """Source numbers cited in an answer, e.g. "[Source 2: ...]" -> {2}."""
    return {int(n) for n in re.findall(r"Source (\d+)", text)}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--pilot"]
    if not args:
        sys.exit('Usage: uv run python query.py [--pilot] "your question"')
    config.configure()
    collection = f"{config.COLLECTION}_pilot" if "--pilot" in sys.argv else config.COLLECTION
    text, sources = answer(" ".join(args), open_index(collection))
    print(text, "\n\nRetrieved:")
    for s in sources:
        mark = "*" if s["n"] in cited(text) else " "
        print(f" {mark} [{s['label']}] {s['score']:.3f}  {s['file'][:70]}")
    print("\n* = cited in the answer")
