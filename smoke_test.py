# smoke_test.py: do the answers cite the right page? Done when 3 of 5 pass.
# Reads eval/smoke.jsonl, one hand-checked question per line:
#   {"question": "...", "file": "exact PDF file name", "page": "12"}
# "page" is the page_label (the page number the PDF viewer shows). A question passes
# if the answer cites at least one source from that file and page.
# Usage: uv run python smoke_test.py
import json
import sys
from pathlib import Path

import config
from query import answer, cited, open_index

SMOKE_FILE = Path("eval/smoke.jsonl")
PASS_MARK = 3


def main():
    if not SMOKE_FILE.exists() or not SMOKE_FILE.read_text().strip():
        sys.exit(f"Add hand-checked questions to {SMOKE_FILE} first (format at the top of this script).")
    cases = [json.loads(line) for line in SMOKE_FILE.read_text().splitlines() if line.strip()]

    config.configure()
    index = open_index()
    passed = 0
    for i, case in enumerate(cases, 1):
        text, sources = answer(case["question"], index)
        cites = [s for s in sources if s["n"] in cited(text)]
        ok = any(s["file"] == case["file"] and s["page"] == str(case["page"]) for s in cites)
        retrieved = any(s["file"] == case["file"] and s["page"] == str(case["page"]) for s in sources)
        passed += ok

        print(f"\n[{i}] {'PASS' if ok else 'FAIL'}  {case['question']}")
        print(f"    expected: {case['file']} p.{case['page']}  (retrieved: {'yes' if retrieved else 'no'})")
        print(f"    cited:    {[f'{s['file'][:40]} p.{s['page']}' for s in cites] or 'nothing'}")
        print(f"    answer:   {text[:300].replace(chr(10), ' ')}")

    print(f"\n{passed}/{len(cases)} cite the right page. "
          f"{'Met' if passed >= PASS_MARK else 'Not met'} (need {PASS_MARK}).")


if __name__ == "__main__":
    main()
