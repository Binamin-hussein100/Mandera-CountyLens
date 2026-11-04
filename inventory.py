# inventory.py: list every PDF in the corpus with its type, year and health flags.
# Read-only: it never changes, moves or deletes the PDFs.
# Usage: uv run python inventory.py [corpus_dir]   (default: CORPUS_DIR from .env)
import csv
import hashlib
import logging
import os
import re
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()
logging.getLogger("pypdf").setLevel(logging.ERROR)  # hide noisy warnings about damaged-but-readable files

OUT_CSV = "inventory.csv"
TEXT_PAGES = 3           # pages sampled to decide whether a PDF is scanned
SCANNED_CHARS = 100      # fewer text characters per sampled page than this = scanned

# First match wins, so the more specific types come first.
DOC_TYPES = [
    ("cbrop",                 r"\bcbrop\b|budget review and outlook"),
    ("budget_implementation", r"implementation report|budget review|quarter|\bq[1-4]\b|\bcbirr\b"),
    ("cidp",                  r"\bcidp\b|integrated development plan"),
    ("adp",                   r"\badp\b|annual development plan"),
    ("fiscal_strategy",       r"\bcfsp\b|fiscal strategy"),
    ("revenue",               r"revenue|finance act|finance bill"),
    ("budget",                r"budget|appropriation|estimates|\bpbb\b"),
    ("audit",                 r"audit"),
    ("progress_report",       r"progress report|\bacpa\b|\bcadp\b|pending bills|statistical abstract|treasury"),
    ("drought_bulletin",      r"drought|early warning|rains assessment|kfssg|food security|seasonal forecast"),
    ("humanitarian",          r"sitrep|situation report|situational|dref|emergency|rapid assessment|outbreak|"
                              r"msna|msni|reach|smart survey|cash|humanitarian|fact ?sheet|unicef|ocha"),
    ("law_policy",            r"\bact\b|\bbill\b|policy|regulations"),
    ("plan_other",            r"plan|strategy|strategic"),
    ("research",              r"case study|a case of|effects? of|impacts? of|influence of|challenges|factors|"
                              r"determinants|thesis|university|analysis|assessment|evaluation|investigation|role of|"
                              r"causes of|relationship|contribution|practices|antecedents|participation"),
]


def classify(name):
    low = name.lower()
    for label, pattern in DOC_TYPES:
        if re.search(pattern, low):
            return label
    return "other"


def find_year(text):
    """Return a financial year like '2023/24', a plan period like '2023-2027', or a single year."""
    # Eight digits with no separator, e.g. "PBB 20222023"
    m = re.search(r"(?<!\d)(20\d{2})(20\d{2})(?!\d)", text)
    if m and int(m.group(2)) == int(m.group(1)) + 1:
        return f"{m.group(1)}/{m.group(2)[-2:]}"
    # Two years together: 2023/24, 2023-24, 2023.24, 2023-2024, 2023/2024
    for m in re.finditer(r"(20\d{2})\s*[/\-.–_]\s*(20\d{2}|\d{2})(?!\d)", text):
        start = int(m.group(1))
        end_raw = m.group(2)
        end = int(end_raw) if len(end_raw) == 4 else (start // 100) * 100 + int(end_raw)
        if end == start + 1:
            return f"{start}/{str(end)[-2:]}"
        if start < end <= start + 6:
            return f"{start}-{end}"
    m = re.search(r"(?<!\d)(20\d{2}|19\d{2})(?!\d)", text)
    return m.group(1) if m else ""


def name_key(name):
    """Normalise a filename so "Report (2).pdf" and "report.pdf" match."""
    stem = re.sub(r"\s*\(\d+\)", "", Path(name).stem.lower())
    stem = re.sub(r"\s*\(id \d+\)", "", stem)
    return re.sub(r"[^a-z0-9]+", "", stem)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def inspect(path):
    """Open the PDF and return pages, encrypted, scanned, broken, first-page text and any error."""
    info = {"pages": "", "encrypted": False, "scanned": False, "broken": False, "error": "", "first_text": ""}
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            info["encrypted"] = True
            reader.decrypt("")  # many "encrypted" PDFs open with an empty password
        info["pages"] = len(reader.pages)
        sample = [reader.pages[i].extract_text() or "" for i in range(min(TEXT_PAGES, len(reader.pages)))]
        info["first_text"] = sample[0][:2000] if sample else ""
        chars = sum(len(t.strip()) for t in sample)
        info["scanned"] = bool(sample) and chars / len(sample) < SCANNED_CHARS
        if info["pages"] == 0:
            info["broken"], info["error"] = True, "no pages"
    except Exception as e:  # pypdf raises many different errors for damaged files
        info["broken"] = True
        info["error"] = f"{type(e).__name__}: {e}"[:200]
    return info


def main():
    corpus = Path(sys.argv[1] if len(sys.argv) > 1 else os.getenv("CORPUS_DIR") or "corpus").expanduser()
    if not corpus.is_dir():
        sys.exit(f"Corpus folder not found: {corpus}")

    pdfs = sorted(p for p in corpus.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
    print(f"Found {len(pdfs)} PDFs in {corpus}")

    rows, first_by_hash, first_by_name = [], {}, {}
    for i, path in enumerate(pdfs, 1):
        print(f"\r[{i}/{len(pdfs)}] {path.name[:70]:<70}", end="", flush=True)
        digest = sha256(path)
        info = inspect(path)
        year = find_year(path.stem) or find_year(info["first_text"])
        rows.append({
            "file": str(path.relative_to(corpus)),
            "size_kb": round(path.stat().st_size / 1024),
            "pages": info["pages"],
            "doc_type": classify(path.stem),
            "year": year,
            "year_from": "filename" if find_year(path.stem) else ("text" if year else ""),
            "duplicate_of": first_by_hash.get(digest, ""),
            "same_name_as": first_by_name.get(name_key(path.name), ""),
            "scanned": info["scanned"],
            "encrypted": info["encrypted"],
            "broken": info["broken"],
            "error": info["error"],
            "sha256": digest,
        })
        first_by_hash.setdefault(digest, str(path.relative_to(corpus)))
        first_by_name.setdefault(name_key(path.name), str(path.relative_to(corpus)))
    print()

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    print(f"\nWrote {OUT_CSV} ({len(rows)} rows)\n")
    print("By type:")
    for label, n in Counter(r["doc_type"] for r in rows).most_common():
        print(f"  {label:<22} {n}")
    print(f"\nDuplicates (identical bytes): {sum(1 for r in rows if r['duplicate_of'])}")
    print(f"Possible duplicates (same name): {sum(1 for r in rows if r['same_name_as'] and not r['duplicate_of'])}")
    print(f"Scanned:    {sum(1 for r in rows if r['scanned'])}")
    print(f"Encrypted:  {sum(1 for r in rows if r['encrypted'])}")
    print(f"Broken:     {sum(1 for r in rows if r['broken'])}")
    print(f"No year:    {sum(1 for r in rows if not r['year'])}")


if __name__ == "__main__":
    main()
