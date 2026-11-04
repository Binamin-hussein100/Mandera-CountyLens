# config.py: settings for Mandera-CountyLens (LlamaIndex). Override any value in .env.
import os
from dotenv import load_dotenv
from llama_index.core import Settings

load_dotenv()

def _int(name, default): return int(os.getenv(name, default))

# Paths
CORPUS_DIR   = os.getenv("CORPUS_DIR", "corpus")
PILOT_DIR    = os.getenv("PILOT_DIR", "corpus_pilot")
CHROMA_DIR   = os.getenv("CHROMA_DIR", "chroma_db")
COLLECTION   = os.getenv("COLLECTION", "mandera")

# Chunking (TOKENS)
CHUNK_SIZE    = _int("CHUNK_SIZE", 256)
CHUNK_OVERLAP = _int("CHUNK_OVERLAP", 50)
TOP_K         = _int("TOP_K", 5)

# Models
LLM_MODEL      = os.getenv("LLM_MODEL", "gpt-4.1-mini")
JUDGE_MODEL    = os.getenv("JUDGE_MODEL", "gpt-5.4-mini")
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "local")
EMBED_MODEL    = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
MAX_AGENT_STEPS = _int("MAX_AGENT_STEPS", 5)

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env (see .env.example).")

def configure():
    """Call once at the top of ingest.py, query.py and agent.py."""
    from llama_index.llms.openai import OpenAI
    Settings.llm = OpenAI(model=LLM_MODEL, temperature=0)
    if EMBED_PROVIDER == "openai":
        from llama_index.embeddings.openai import OpenAIEmbedding
        Settings.embed_model = OpenAIEmbedding(model=EMBED_MODEL)
    else:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)

SYSTEM_PROMPT = """..."""  # keep the prompt from my last message (with the year, numbers, language and injection rules)