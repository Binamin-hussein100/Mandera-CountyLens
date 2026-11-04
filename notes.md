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

### To follow up
- The CIDP 2023–2027 is scanned, so the target question's "CIDP target" step needs OCR (Week 10).
- Two files aren't about Mandera: `JS_DOM_Group_Project.pdf` and `Asynchronous_JavaScript_Architecture.pptx`.
- Types come from filename keywords, so spot-check `doc_type` for any file that matters.
- Still no year (no date in the document): Organizational Structure, the Kiswahili thesis, the curbing-terrorist-threats thesis, JS_DOM_Group_Project.
