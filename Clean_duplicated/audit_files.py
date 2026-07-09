"""
audit_files.py - Phase 3 of the TTP extraction pipeline (deduplication + language filter).

- Automatically collects the original PDFs and their converted TXT
  counterparts from Conversion_TXT (Phase 2 output), using
  Conversion_TXT/pdf_processed as the source of truth for which reports have
  already been converted.
- Creates PDF_dedup/ and TXT_dedup/ folders with unique files (no content
  duplicates, compared by hash).
- For each group of duplicates, picks the representative with the shortest
  name that has a counterpart in the other folder; if there is no
  counterpart, picks the one with the shortest name overall.
- Filters out pairs whose TXT is not written in English.
- Generates audit_report.csv with only the resulting (PDF + TXT) pairs that
  are in English.

All paths are computed from this file's own location
(Path(__file__).resolve()), so the script can be run from any computer
without editing hardcoded paths, as long as the project folder layout is
preserved.
"""

import csv
import hashlib
import shutil
from collections import defaultdict
from pathlib import Path

from langdetect import detect, LangDetectException

# =========================================================================
# CONFIGURATION - absolute paths derived from the project layout
# =========================================================================

ROOT = Path(__file__).resolve().parent           # Clean_duplicated/
PROJECT_ROOT = ROOT.parent                        # pipeline_ttp_extraction/
CONVERSION_DIR = PROJECT_ROOT / "Conversion_TXT"  # Phase 2 folder

# Phase 2 raw output: one "<stem>_output" folder per PDF that has already
# been converted. Used here as the reference list of report stems that are
# ready to be deduplicated.
PDF_PROCESSED_DIR = CONVERSION_DIR / "pdf_processed"

# Original PDF reports (Phase 1 output / Phase 2 input), split across
# batches.
REPORTS_DIRS = [
    CONVERSION_DIR / "ReportsA",
    CONVERSION_DIR / "ReportsB",
    CONVERSION_DIR / "ReportsC",
    CONVERSION_DIR / "ReportsCTI_HAL",
]

# Final converted TXT files (Phase 2 output), split across the same batches.
TXT_OUT_DIRS = [
    CONVERSION_DIR / "txt_out_A",
    CONVERSION_DIR / "txt_out_B",
    CONVERSION_DIR / "txt_out_C",
    CONVERSION_DIR / "txt_out_CTI_HAL",
]

# Phase 3 output (deduplicated + English-only pairs), consumed by Phase 4.
PDF_OUT = ROOT / "PDF_dedup"
TXT_OUT = ROOT / "TXT_dedup"
OUTPUT_CSV = ROOT / "audit_report.csv"

HASH_ALGO = "md5"


# ── helpers ──────────────────────────────────────────────────────────────────

def file_hash(path: Path) -> str:
    h = hashlib.new(HASH_ALGO)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def processed_stems(pdf_processed_dir: Path) -> set[str]:
    """
    Returns the set of report stems that already have Phase 2 output
    (a "<stem>_output" folder) inside Conversion_TXT/pdf_processed.
    """
    if not pdf_processed_dir.exists():
        return set()
    return {
        entry.name[: -len("_output")]
        for entry in pdf_processed_dir.iterdir()
        if entry.is_dir() and entry.name.endswith("_output")
    }


def collect_by_stem(folders: list[Path], pattern: str, allowed_stems: set[str]) -> dict[str, Path]:
    """
    Walks a list of folders looking for files matching `pattern` (e.g. "*.pdf"),
    keeping only one file per stem that is present in `allowed_stems`.
    """
    found: dict[str, Path] = {}
    for folder in folders:
        if not folder.exists():
            continue
        for path in folder.rglob(pattern):
            if path.stem in allowed_stems and path.stem not in found:
                found[path.stem] = path
    return found


def group_by_hash(paths) -> dict[str, list[Path]]:
    """Returns {hash: [Path, ...]} for the given collection of file paths."""
    groups: dict[str, list[Path]] = defaultdict(list)
    for p in sorted(paths):
        groups[file_hash(p)].append(p)
    return groups


def is_english(txt_path: Path, sample_chars: int = 2000) -> bool:
    """Returns True if the text file is detected as English."""
    try:
        text = txt_path.read_text(encoding="utf-8", errors="ignore")[:sample_chars].strip()
        if not text:
            return False
        return detect(text) == "en"
    except LangDetectException:
        return False


def pick_representative(paths: list[Path], preferred_stems: set[str]) -> Path:
    """
    From a duplicate group, picks the path whose stem is in preferred_stems
    (i.e. it has a counterpart in the other folder). Tie-break: shortest name.
    """
    preferred = [p for p in paths if p.stem in preferred_stems]
    pool = preferred if preferred else paths
    return min(pool, key=lambda p: len(p.name))


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    PDF_OUT.mkdir(exist_ok=True)
    TXT_OUT.mkdir(exist_ok=True)

    print(f"Conversion_TXT folder: {CONVERSION_DIR}")
    processed = processed_stems(PDF_PROCESSED_DIR)
    print(f"Report stems with Phase 2 output: {len(processed)}")

    print("Locating original PDFs for processed reports...")
    pdf_by_stem = collect_by_stem(REPORTS_DIRS, "*.pdf", processed)

    print("Locating converted TXTs for processed reports...")
    txt_by_stem = collect_by_stem(TXT_OUT_DIRS, "*.txt", processed)

    print("Grouping PDFs by hash...")
    pdf_groups = group_by_hash(pdf_by_stem.values())

    print("Grouping TXTs by hash...")
    txt_groups = group_by_hash(txt_by_stem.values())

    # Stems available in each set
    all_pdf_stems = {p.stem for paths in pdf_groups.values() for p in paths}
    all_txt_stems = {p.stem for paths in txt_groups.values() for p in paths}

    # Choose a representative for each group, prioritizing those with a counterpart
    print("Selecting representatives...")
    pdf_reps: dict[str, tuple[Path, str]] = {}   # stem -> (path, hash)
    for h, paths in pdf_groups.items():
        rep = pick_representative(paths, all_txt_stems)
        pdf_reps[rep.stem] = (rep, h)

    txt_reps: dict[str, tuple[Path, str]] = {}
    for h, paths in txt_groups.items():
        rep = pick_representative(paths, all_pdf_stems)
        txt_reps[rep.stem] = (rep, h)

    # Only the pairs whose stems match on both sides
    common_stems = sorted(set(pdf_reps) & set(txt_reps))

    # Filter by English language
    print("Detecting the language of each TXT...")
    english_stems = []
    non_english_stems = []
    for stem in common_stems:
        txt_src, _ = txt_reps[stem]
        if is_english(txt_src):
            english_stems.append(stem)
        else:
            non_english_stems.append(stem)

    common_stems = english_stems

    # Copy to output folders
    print(f"Copying {len(common_stems)} English pairs to PDF_dedup / TXT_dedup...")
    rows = []
    for stem in common_stems:
        pdf_src, pdf_h = pdf_reps[stem]
        txt_src, txt_h = txt_reps[stem]

        shutil.copy2(pdf_src, PDF_OUT / pdf_src.name)
        shutil.copy2(txt_src, TXT_OUT / txt_src.name)

        rows.append({
            "name":     stem,
            "pdf_path": str((PDF_OUT / pdf_src.name).relative_to(ROOT)),
            "pdf_hash": pdf_h,
            "txt_path": str((TXT_OUT / txt_src.name).relative_to(ROOT)),
            "txt_hash": txt_h,
        })

    # CSV
    fieldnames = ["name", "pdf_path", "pdf_hash", "txt_path", "txt_hash"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    total_pdf_orig = sum(len(v) for v in pdf_groups.values())
    total_txt_orig = sum(len(v) for v in txt_groups.values())
    dup_pdf = total_pdf_orig - len(pdf_reps)
    dup_txt = total_txt_orig - len(txt_reps)
    only_pdf = len(set(pdf_reps) - set(txt_reps))
    only_txt = len(set(txt_reps) - set(pdf_reps))

    print(f"\n{'=' * 52}")
    print(f"Original PDFs:              {total_pdf_orig}")
    print(f"  duplicates removed:       {dup_pdf}")
    print(f"Original TXTs:              {total_txt_orig}")
    print(f"  duplicates removed:       {dup_txt}")
    print(f"No PDF counterpart (skipped): {only_pdf}")
    print(f"No TXT counterpart (skipped): {only_txt}")
    print(f"Non-English (removed):      {len(non_english_stems)}")
    print(f"Unique pairs in CSV:        {len(common_stems)}")
    print(f"\nFolders created: {PDF_OUT.name}/  {TXT_OUT.name}/")
    print(f"CSV generated at: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
