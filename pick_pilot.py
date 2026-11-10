# pick_pilot.py: copy ~50 text PDFs, spread across types and years, into corpus_pilot/.
# Reads inventory.csv (including any hand corrections) and never changes the originals.
# Usage: uv run python pick_pilot.py [--dry-run]
import csv
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path(os.getenv("RAW_DIR") or "raw").expanduser()
PILOT_DIR = Path(os.getenv("PILOT_DIR") or "corpus_pilot")
INVENTORY = "inventory.csv"
PILOT_LIST = "pilot.csv"

# PDFs per type (50 total). Weighted towards budgets and plans, which most questions are about.
QUOTAS = {
    "budget": 8,
    "budget_implementation": 6,
    "adp": 5,
    "fiscal_strategy": 4,
    "revenue": 3,
    "audit": 3,
    "cidp": 2,
    "cbrop": 2,
    "progress_report": 1,
    "law_policy": 2,
    "plan_other": 2,
    "drought_bulletin": 5,
    "humanitarian": 4,
    "research": 3,
}

# Years picked first for these types, so the target question
# (health allocation FY 2022/23 vs FY 2023/24) can be tried on the pilot.
PRIORITY_YEARS = {
    "budget": ["2022/23", "2023/24"],
    "budget_implementation": ["2022/23", "2023/24"],
}


def usable(row):
    """Text PDFs only: no scanned, broken or copied files, and a known year."""
    return (row["scanned"] == "False" and row["broken"] == "False"
            and not row["duplicate_of"] and not row["same_name_as"]
            and row["year"] and row["doc_type"] in QUOTAS)


def spread(items, k):
    """Pick k items evenly spaced through a sorted list."""
    if k >= len(items):
        return list(items)
    if k == 1:
        return [items[len(items) // 2]]
    return [items[round(i * (len(items) - 1) / (k - 1))] for i in range(k)]


def pick(rows, quota, priority):
    """Take one PDF per year in rounds, so each type covers as many years as possible."""
    by_year = defaultdict(list)
    for r in sorted(rows, key=lambda r: r["file"]):
        by_year[r["year"]].append(r)

    chosen = []
    for year in priority:
        if by_year.get(year) and len(chosen) < quota:
            chosen.append(by_year[year].pop(0))
    while len(chosen) < quota:
        years = sorted(y for y, files in by_year.items() if files)
        if not years:
            break
        for year in spread(years, quota - len(chosen)):
            chosen.append(by_year[year].pop(0))
    return chosen


def main():
    dry_run = "--dry-run" in sys.argv
    rows = [r for r in csv.DictReader(open(INVENTORY, encoding="utf-8")) if usable(r)]

    by_type = defaultdict(list)
    for r in rows:
        by_type[r["doc_type"]].append(r)

    selection = []
    for doc_type, quota in QUOTAS.items():
        picked = pick(by_type[doc_type], quota, PRIORITY_YEARS.get(doc_type, []))
        if len(picked) < quota:
            print(f"  note: only {len(picked)} usable {doc_type} PDFs (wanted {quota})")
        selection += picked

    print(f"Selected {len(selection)} PDFs:\n")
    for r in selection:
        print(f"  {r['doc_type']:<22} {r['year']:<10} {r['file'][:80]}")

    if dry_run:
        print("\nDry run: nothing copied.")
        return

    PILOT_DIR.mkdir(exist_ok=True)
    copied = 0
    for r in selection:
        src, dst = RAW_DIR / r["file"], PILOT_DIR / Path(r["file"]).name
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            continue
        shutil.copy2(src, dst)
        copied += 1

    with open(PILOT_LIST, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "doc_type", "year", "pages"])
        writer.writeheader()
        writer.writerows({k: r[k] for k in writer.fieldnames} for r in selection)

    chosen = {Path(r["file"]).name for r in selection}
    extra = [p.name for p in PILOT_DIR.glob("*.pdf") if p.name not in chosen]
    print(f"\nCopied {copied} new PDFs to {PILOT_DIR}/ ({len(selection)} selected). List saved to {PILOT_LIST}.")
    if extra:
        print(f"Warning: {len(extra)} PDFs in {PILOT_DIR}/ are not in this selection: {extra[:5]}")


if __name__ == "__main__":
    main()
