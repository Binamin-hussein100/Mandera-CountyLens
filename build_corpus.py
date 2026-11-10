# build_corpus.py: copy every usable text PDF from RAW_DIR into CORPUS_DIR (corpus/).
# Reads inventory.csv (including hand corrections). Never changes or deletes the originals.
# Skips scanned, broken and duplicate PDFs, and files not about Mandera.
# Usage: uv run python build_corpus.py [--dry-run]
import csv
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path(os.getenv("RAW_DIR") or "raw").expanduser()
CORPUS_DIR = Path(os.getenv("CORPUS_DIR") or "corpus")
INVENTORY = "inventory.csv"
NOT_MANDERA = {"JS_DOM_Group_Project.pdf"}  # text PDFs that are off-topic


def skip_reason(row):
    """Why a PDF is left out, or "" if it goes into the corpus."""
    if row["broken"] == "True":
        return "broken"
    if row["scanned"] == "True":
        return "scanned"
    if row["duplicate_of"] or row["same_name_as"]:
        return "duplicate"
    if Path(row["file"]).name in NOT_MANDERA:
        return "not about Mandera"
    return ""


def main():
    dry_run = "--dry-run" in sys.argv
    rows = list(csv.DictReader(open(INVENTORY, encoding="utf-8")))
    keep = [r for r in rows if not skip_reason(r)]
    skipped = Counter(skip_reason(r) for r in rows if skip_reason(r))

    print(f"{len(rows)} PDFs in {INVENTORY}: keeping {len(keep)}, skipping {sum(skipped.values())} {dict(skipped)}")
    if dry_run:
        print("Dry run: nothing copied.")
        return

    CORPUS_DIR.mkdir(exist_ok=True)
    copied = 0
    for r in keep:
        src, dst = RAW_DIR / r["file"], CORPUS_DIR / Path(r["file"]).name
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            continue  # already copied
        shutil.copy2(src, dst)
        copied += 1

    names = {Path(r["file"]).name for r in keep}
    extra = sorted(p.name for p in CORPUS_DIR.glob("*.pdf") if p.name not in names)
    total = len(list(CORPUS_DIR.glob("*.pdf")))
    print(f"Copied {copied} new PDFs. {CORPUS_DIR}/ now holds {total} PDFs.")
    if extra:
        print(f"Warning: {len(extra)} PDFs in {CORPUS_DIR}/ are no longer selected (not deleted): {extra[:5]}")


if __name__ == "__main__":
    main()
