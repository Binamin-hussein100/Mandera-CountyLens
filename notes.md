# Notes

## Corpus inventory (4 Nov 2026)

Source: `inventory.py` → `inventory.csv`, run over `/Users/mac/Downloads/Mandera`. 77 rows corrected by hand afterwards (26 types, 60 years); hand-set years have `year_from = manual`.

| | Count |
|---|---|
| PDFs | 552 |
| Pages | 21,207 |
| Exact duplicates (identical bytes) | 0 |
| Possible duplicates (same name, different file) | 12 |
| Scanned (no text layer, needs OCR) | 97 |
| Unreadable (broken or encrypted) | 0 |
| No year found | 4 |

**Budget and plan documents:** 140 PDFs (11,509 pages), all with a year. 27 are scanned, including both CIDPs, 2018–2022 and 2023–2027.

### By type

| Type | PDFs | Scanned |
|---|---|---|
| drought_bulletin | 189 | 0 |
| research | 118 | 58 |
| humanitarian | 50 | 1 |
| budget_implementation | 31 | 3 |
| budget | 31 | 2 |
| audit | 25 | 14 |
| law_policy | 24 | 2 |
| adp | 18 | 0 |
| plan_other | 14 | 3 |
| revenue | 13 | 5 |
| progress_report | 12 | 4 |
| fiscal_strategy | 9 | 0 |
| cidp | 5 | 3 |
| other | 5 | 2 |
| cbrop | 8 | 0 |

7 CBROPs were first labelled budget_implementation by a rule-order bug in `inventory.py`. They were relabelled in the CSV, and the rule is fixed.

Budget and plan types: budget, budget_implementation, adp, cidp, fiscal_strategy, cbrop, revenue, audit.

### Budget and plan documents by financial year

| FY | PDFs | FY | PDFs |
|---|---|---|---|
| 2013/14 | 2 | 2021/22 | 10 |
| 2014/15 | 2 | 2022/23 | 9 |
| 2015/16 | 4 | 2023/24 | 9 |
| 2016/17 | 3 | 2024/25 | 11 |
| 2017/18 | 7 | 2025/26 | 9 |
| 2018/19 | 9 | 2026/27 | 1 |
| 2019/20 | 7 | 2027/28 | 2 |
| 2020/21 | 9 | | |

The FY rows add up to 94. The other 46: 41 carry only a calendar year (Acts, audit reports dated "FY ended 30 June 2025", and similar), and 5 are plan periods (CIDPs 2013–2017, 2018–2022 ×3, 2023–2027).

### Whole corpus by year (first year of the range)

| Year | PDFs | Year | PDFs |
|---|---|---|---|
| ≤2012 | 26 | 2020 | 30 |
| 2013 | 17 | 2021 | 36 |
| 2014 | 50 | 2022 | 34 |
| 2015 | 53 | 2023 | 44 |
| 2016 | 34 | 2024 | 54 |
| 2017 | 27 | 2025 | 51 |
| 2018 | 40 | 2026 | 16 |
| 2019 | 34 | 2027 | 2 |
| | | none | 4 |

## Full index build (10 Nov 2026)

`uv run python ingest.py --full`: corpus/ → Chroma collection `mandera`. MiniLM on the laptop CPU (Mac), 256-token chunks with 50 overlap.

| | Full corpus | Pilot |
|---|---|---|
| Documents (PDFs) | 449 | 50 |
| Pages | 18,405 | 3,967 |
| Chunks (= Chroma count) | 61,320 | 13,931 |
| Time to read PDFs | 388 s | ~95 s |
| Time to chunk, embed and store | 351 s | ~80 s |
| Total build time | 739 s (12.3 min) | 173 s |
| Rerun with nothing changed | not measured yet (≈ reading time, ~6.5 min) | 101 s |

Index size on disk: `chroma_db/` is 1.3 GB in total. That holds both collections plus their docstores (`mandera_docstore.json` 95 MB, pilot 21 MB), and the chunk text and metadata stored in `chroma.sqlite3` (1.0 GB). The vector index for `mandera` alone is 120 MB.

Reading the PDFs takes about half the build time, so a rerun can't drop below ~6.5 min. Chunking and embedding are the half the docstore saves.

Test query "How much was allocated to health in FY 2022/23?" still returns the CoB CBIRR FY 2023/24 first (3 of 5). The full corpus adds a 2019/20 policy brief and a 2021/22 budget. None are FY 2022/23.

## Pilot vs full index (10 Nov 2026, no year filter)

Same three questions, same settings, top 5.

| Question | Pilot (50 PDFs) | Full (449 PDFs) | Better or worse? |
|---|---|---|---|
| Health allocation FY 2022/23 | "I don't know". All 5 from the CoB CBIRR 2023/24. | "I don't know". CBIRR 2023/24 ×3, policy brief 2019/20, budget 2021/22. No 2022/23. | Same (wrong years either way) |
| The county's OSR target (no year) | "I don't know", citing Bomet and Kitui figures | Cited the all-county total and **Baringo's** FY 2021/22 target, plus Mandera 2024/25 reports | Worse: more national CoB reports, more other counties |
| Mandera's OSR target FY 2023/24 | "I don't know". Top 5 from 2022/23, 2025, 2020/21, 2020. | Partial: gave two stream targets (land rents 71,055,477; plot fees 52,590,771) from Q2 BIR FY 2023/24 p. 10, but "total not provided". Other 4 chunks from 2021/22 and 2022/23. | Better: reached the right document, one page off |

**What this shows**
- More documents means more years and more CoB national reports competing. The year can't be read from similarity alone: only 1 of the top 5 was FY 2023/24, even with the year in the question.
- **The answer to Q3 is KSh 336,533,846** (checked in the text, still to confirm by hand in the PDF), in three places:
  - `Quarter 2 Budget Implementation Report FY 2023.2024.pdf`, PDF p. 9: "Grand Total 336,533,846" (stream table, column headers on the page before)
  - same file, PDF p. 11: "Local Revenue Collections | Annual Targeted Revenue 336,533,846" (Table 4)
  - `Mandera DRAFT PBB FY 23.24 (id 296).pdf`, p. 4 (draft budget: same figure)
- **Why it was missed: the table is split across pages.** The column header "Target 2023/2024" is on p. 10, and the "Grand Total" row is at the bottom of p. 9 with no header. A chunk holding only numbers and "Grand Total" doesn't look like "own-source revenue target" to MiniLM. Table 4 on p. 11 does name it, but as "Local Revenue Collections", the same synonym problem as the CBROP.
- The draft PBB p. 4 wasn't retrieved by either index.

## Query tests (pilot index, no year filter, 9 Nov 2026)

Setup: 50-PDF pilot, MiniLM, chunks of 256 tokens with 50 overlap, top 5, gpt-4.1-mini.

| # | Question | Top 5 retrieved | Answer | Right page retrieved? |
|---|---|---|---|---|
| 1 | What is the county's own-source revenue target? | 3 from the CoB CBIRR FY 2023/24 (national report, all counties), 2 Mandera CBROPs (2018/19, 2026) | "I don't know". It cited other counties' figures (Bomet, Kitui). | No |
| 2 | What is Mandera County's own-source revenue target for FY 2023/24? | All 5 Mandera documents, but the wrong years: Q1 BIR 2022/23, PBB 2022/23, CFSP 2025, Q2 BIR 2020/21, CFSP 2020 | "I don't know". It said the excerpts cover 2022/23 and other years, not 2023/24. | No |

**What this shows**
- Naming "Mandera" moved the search from the all-county CoB report to Mandera's own documents.
- Naming "FY 2023/24" didn't bring back FY 2023/24 documents. The embedding can't tell the years apart, so this needs the year filter.
- Both refusals were correct: the model didn't guess or borrow other counties' numbers as Mandera's.
- The two Mandera CBROPs retrieved for Q1, checked:
  - **CBROP 2018/19, p. 23: the target is there, written as text, not in a table.** "We thus expect a local revenue collection of over 100 million for FY 2019/2020." The model missed it because the document says "local revenue" and the question says "own-source revenue". It's also a FY 2019/20 figure. Hybrid search (BM25) won't fix a synonym. That needs query expansion, or a note in the prompt that local revenue = own-source revenue (OSR).
  - **CBROP 2026, p. 25: no target figure.** The page discusses performance against targets without giving a number, so retrieval chose the wrong page. The page number printed on it is 28, while `page_label` is 25 (the PDF defines no page labels, so it falls back to the PDF page number). Citations therefore give the page your PDF viewer shows, not the printed one.
- Likely answer (to check by hand): `Mandera DRAFT PBB FY 23.24 (id 296).pdf`, p. 4, "County Own Source revenue 336,533,846". It's a draft, and the approved figure may differ.

### To follow up
- The CIDP 2023–2027 is scanned, so the target question's "CIDP target" step needs OCR (Week 10).
- Two files aren't about Mandera: `JS_DOM_Group_Project.pdf` and `Asynchronous_JavaScript_Architecture.pptx`.
- Types come from filename keywords, so spot-check `doc_type` for any file that matters.
- Still no year (no date in the document): Organizational Structure, the Kiswahili thesis, the curbing-terrorist-threats thesis, JS_DOM_Group_Project.
