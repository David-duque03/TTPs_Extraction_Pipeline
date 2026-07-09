# Clean_duplicated (Phase 3 — Deduplication + language filter)

This module removes content-duplicate reports and keeps only the reports
written in English, producing the final (PDF + TXT) pairs consumed by
Phase 4 (`extracts_ttps/`). This is Phase 3 of the TTP extraction pipeline
(see the project's root `README.md` for the full pipeline overview).

## Input (automatic, no manual copying required)

The script reads directly from the Phase 2 output in `Conversion_TXT/`:

- `Conversion_TXT/pdf_processed/` is used as the reference list of report
  stems that have already been converted to text (one `<stem>_output` folder
  per report).
- The original PDFs for those stems are located in
  `Conversion_TXT/ReportsA`, `ReportsB`, `ReportsC` and `ReportsCTI_HAL`.
- The converted TXTs for those stems are located in
  `Conversion_TXT/txt_out_A`, `txt_out_B`, `txt_out_C` and `txt_out_CTI_HAL`.

All of these paths are computed automatically from this script's location
(`Path(__file__).resolve().parent`), so nothing needs to be edited or copied
before running it, as long as the project folder layout is preserved and
Phase 2 has already been run.

## Requirements

- Conda or Miniconda
- Python 3.10 or higher

## Create the conda environment

From this folder:

```bash
conda env create -f environment.yml
conda activate limpieza_duplicados
```

## Execution

```bash
python audit_files.py
```

## Output

When it finishes, the following are created or updated in this folder:

- `PDF_dedup/`: unique, paired PDFs
- `TXT_dedup/`: unique, paired TXTs — this is the input folder for Phase 4
  (`extracts_ttps/process_files.py`)
- `audit_report.csv`: report with columns:
  - `name`
  - `pdf_path`
  - `pdf_hash`
  - `txt_path`
  - `txt_hash`

## Notes

- Deduplication is done by content hash (`md5`), not by file name.
- When several copies share the same content, the one that has a counterpart
  in the other folder (PDF <-> TXT) is preferred, with the shortest name as
  a tie-breaker.
- Files without a PDF/TXT counterpart are not included in the final CSV.
- Only reports whose text was detected as English (via `langdetect`) are
  kept.
