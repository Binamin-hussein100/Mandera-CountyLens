# Mandera-CountyLens

Ask questions about Mandera County's public budgets, development plans (CIDPs, ADPs), fiscal strategy papers and revenue documents, and get answers cited to the exact document, financial year and page, for example `[Source 1: FY 2023/24 Budget | p. 12]`. If the documents don't cover the question, it says "I don't know".

Built with [LlamaIndex](https://www.llamaindex.ai/), Chroma and MiniLM embeddings.

> **Status (10 Nov 2026): Week 2, first full index.** All 449 text PDFs are indexed and the system answers with page citations. It doesn't yet pick the right financial year by itself, so questions that name a year often retrieve other years' documents. A year filter and hybrid search are next. Measured results are in [notes.md](notes.md).

## The corpus

552 public PDFs about Mandera County, collected by hand. Where they came from is in [sources.md](sources.md), and every file is listed in [inventory.csv](inventory.csv) with its type, year and condition.

| | PDFs | Pages |
|---|---|---|
| Collected | 552 | 21,207 |
| **Indexed (text PDFs)** | **449** | **18,405** |
| Left out: scanned images (OCR planned for Week 10) | 97 | |
| Left out: duplicate copies | 5 | |
| Left out: not about Mandera | 1 | |

Of the collected PDFs, 140 are county budget and planning documents covering FY 2013/14 to FY 2027/28: budgets, budget implementation reports, ADPs, CIDPs, fiscal strategy papers, CBROPs, revenue documents and audits. The rest are drought bulletins (189), research papers (118), humanitarian reports (50) and other county documents. 27 of the budget and planning documents are scanned, including the CIDP 2023–2027, so they aren't searchable yet.

**The index:** 61,320 chunks of 256 tokens. A full build takes about 12 minutes on a laptop CPU, and a rerun only re-embeds changed files.

The PDFs and the index are not in this repo.

## How to run it

**Requirements:** Python 3.14, [uv](https://docs.astral.sh/uv/), and an OpenAI API key (for answering; embeddings run locally).

```bash
# 1. Install
uv sync

# 2. Configure: copy the template and fill in OPENAI_API_KEY and RAW_DIR (the folder holding your PDFs)
cp .env.example .env

# 3. Build the corpus
uv run python inventory.py      # list every PDF in RAW_DIR -> inventory.csv (type, year, scanned, duplicate)
uv run python build_corpus.py   # copy usable text PDFs into corpus/

# 4. Build the index
uv run python ingest.py --full  # chunk, embed and store in chroma_db/ (~12 min first time)

# 5. Ask a question
uv run python query.py "What is Mandera County's own-source revenue target for FY 2023/24?"
```

`query.py` prints the answer, the five passages it was given, and which ones it cited.

**Notes**
- Running `inventory.py` again overwrites `inventory.csv`, including any corrections made by hand.
- To try things quickly, `uv run python pick_pilot.py` copies a 50-PDF sample into `corpus_pilot/`. Then use `uv run python ingest.py` and `uv run python query.py --pilot "..."`.
- Add `--rebuild` to `ingest.py` after changing the chunk size or the embedding model.

## How it works

1. **Inventory:** every PDF gets a document type and financial year (from the file name, or its first page), and is checked for scans, damage and duplicates.
2. **Load:** each page becomes one document carrying its file name, page number, type and year.
3. **Chunk and embed:** pages are split into 256-token chunks. Each chunk is embedded with MiniLM, together with its type and year.
4. **Store:** chunks go into Chroma. A docstore remembers what's already indexed, so reruns skip unchanged pages.
5. **Answer:** the question is embedded, the 5 closest chunks are retrieved, and the LLM answers only from them. It cites each claim by source label and refuses when they don't contain the answer.

## Project files

| File | What it does |
|---|---|
| `config.py` | Settings (paths, chunk size, models) and the system prompt |
| `inventory.py` | Lists and classifies every PDF → `inventory.csv` |
| `build_corpus.py` | Copies usable text PDFs into `corpus/` |
| `pick_pilot.py` | Copies a 50-PDF sample spread across types and years → `corpus_pilot/`, `pilot.csv` |
| `ingest.py` | Loads, chunks, embeds and stores the PDFs in Chroma |
| `query.py` | Answers a question with citations |
| `smoke_test.py` | Checks whether answers cite the expected page (`eval/smoke.jsonl`) |
| `notes.md` | Corpus counts, build times and query test results |
| `sources.md` | Where the documents came from |

## Known issues

- **No year filter yet.** Similar documents from different years compete, and the right year often isn't in the top 5.
- **National reports mix in other counties.** The Controller of Budget reports cover all 47 counties, so other counties' figures can be retrieved.
- **Budget tables split across pages lose their headers**, and some documents say "local revenue" where questions say "own-source revenue". Both make figures hard to find.
- **Scanned PDFs aren't searchable** until OCR is added.

## Roadmap

| Version | Scope |
|---|---|
| v1: RAG (Weeks 2–4) | Full index ✓, year filter, 50-question eval set, Recall@5/MRR, faithfulness judge, hybrid search, question router, live demo |
| v2: Service (Weeks 5–6) | FastAPI with roles, MCP tools, LangGraph agent with a verifier |
| v3: Agent (Weeks 7–11) | Cloud deployment, cost caps, CI eval gates, guardrails, OCR |
