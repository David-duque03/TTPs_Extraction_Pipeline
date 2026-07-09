# pipeline_ttp_extraction

An end-to-end pipeline that extracts MITRE ATT&CK Tactics, Techniques and
Procedures (TTPs) and Indicators of Compromise (IoCs) from Cyber Threat
Intelligence (CTI) PDF reports, using [TTPXHunter](https://github.com/dessertlab/TTPXHunter)
for TTP classification and regex-based extraction for IoCs. The pipeline is
organized into six phases, four of which are implemented as standalone
scripts in this repository (Phases 2 through 6, Phases 4-5-6 sharing one
module); Phase 1 is a manual/external data-collection step.

## Pipeline overview

```
Phase 1: PDF collection (manual, external)
    -> raw CTI PDF reports, placed into Conversion_TXT/ReportsX/
        |
        v
Phase 2: Conversion_TXT/          (PDF -> TXT, incl. image OCR via Qwen2-VL/LM Studio)
        |
        v
Phase 3: Clean_duplicated/        (deduplication by content hash + English-only filter)
        |
        v
Phase 4 + 5 + 6: extracts_ttps/   (TTP extraction via TTPXHunter, IoC extraction via
                                    regex, merge into dataset_completo.json + cleanup)
        |
        v
Statistical analysis: dataset_analysis/  (plots and summaries from the final dataset)
```

Each phase is self-contained in its own folder and reads its input directly
from the previous phase's output folder, using paths computed at runtime
from `Path(__file__).resolve().parent`. This means the whole project can be
copied to any computer/drive without editing any hardcoded paths, as long as
the folder layout described below is preserved.

## Folder layout

```
pipeline_ttp_extraction/
├── Conversion_TXT/        # Phase 2 - PDF -> TXT conversion (+ image OCR)
│   ├── ReportsA/ ReportsB/ ReportsC/ ReportsCTI_HAL/   # Input PDFs (Phase 1 output)
│   ├── pdf_processed/                                   # Phase 2 raw output
│   ├── txt_out_A/ txt_out_B/ txt_out_C/ txt_out_CTI_HAL/ # Phase 2 final TXT output
│   ├── utils/
│   ├── main.py
│   ├── conversion_txt.yml
│   └── README.md
├── Clean_duplicated/       # Phase 3 - deduplication + English-language filter
│   ├── PDF_dedup/ TXT_dedup/     # Output (created at runtime)
│   ├── audit_files.py
│   ├── environment.yml
│   └── README.md
├── extracts_ttps/          # Phases 4+5+6 - TTP + IoC extraction, dataset build
│   ├── label_dict.pkl          # TTPXHunter label map (place manually, see README)
│   ├── ttp_id_name.pkl         # TTPXHunter technique-id map (place manually, see README)
│   ├── dataset_completo.json          # Phase 4+5+6 output
│   ├── dataset_completo_limpio.json   # Cleaned dataset
│   ├── process_files.py
│   ├── clean_dataset.py
│   ├── environment.yml
│   └── README.md
├── dataset_analysis/       # Statistical analysis (plots, summaries)
│   ├── output_dataset_limpio_v2.csv   # Input CSV (generate manually, see README)
│   ├── plots_iocs_enrique/            # Output (created at runtime)
│   ├── plots_new_iocs_filtered/       # Output (created at runtime)
│   ├── analisis_ttp_dataset_vEnrique.py
│   ├── clean_dataset.py               # Convenience copy of extracts_ttps/clean_dataset.py
│   ├── environment.yml
│   └── README.md
└── README.md                # This file
```

## Phases in detail

### Phase 1 — PDF collection (manual, external)

Not implemented as a script in this repository. Public CTI reports (from
sources such as vendor blogs, threat intel feeds, etc.) are collected
manually and placed as PDF files into `Conversion_TXT/ReportsA/`,
`ReportsB/`, `ReportsC/` and `ReportsCTI_HAL/` (one subfolder per batch).

### Phase 2 — PDF to TXT conversion (`Conversion_TXT/`)

Extracts text from each PDF page with PyMuPDF, extracts embedded
images/screenshots, and transcribes those images with the
`Qwen2-VL-7B-Instruct` vision-language model served locally through LM
Studio, inserting the transcriptions back into the text at the position
where each image appeared. Produces one final `.txt` file per PDF, in
`txt_out_<batch>/`.

See [`Conversion_TXT/README.md`](Conversion_TXT/README.md) for setup and
usage details.

### Phase 3 — Deduplication and language filter (`Clean_duplicated/`)

Reads the Phase 2 output (`Conversion_TXT/pdf_processed/` as the reference
list of already-converted reports, cross-referenced with the `ReportsX/`
and `txt_out_X/` folders), groups reports by content hash to detect
duplicates, keeps only one copy of each unique report, and filters out
non-English reports using `langdetect`. Produces deduplicated,
English-only PDF/TXT pairs in `PDF_dedup/` and `TXT_dedup/`.

See [`Clean_duplicated/README.md`](Clean_duplicated/README.md) for setup
and usage details.

### Phases 4, 5 and 6 — TTP extraction, IoC extraction, dataset build (`extracts_ttps/`)

Reads every `.txt` file from `Clean_duplicated/TXT_dedup/` and, for each
report:

- **Phase 4:** runs the TTPXHunter model over each sentence to detect
  MITRE ATT&CK techniques, keeping only predictions above a 0.9 confidence
  threshold.
- **Phase 5:** scans the same text with regular expressions to extract
  IoCs (IPv4/IPv6 addresses, MD5/SHA1/SHA256 hashes, URLs).
- **Phase 6:** merges the Phase 4 and Phase 5 results into a single
  structured JSON record per report, saved to `dataset_completo.json`. An
  optional cleanup step (`clean_dataset.py`) removes TTP entries whose
  context is a failed/empty image-OCR transcription rather than real
  report text, producing `dataset_completo_limpio.json`.

This phase requires `label_dict.pkl` and `ttp_id_name.pkl` from the
TTPXHunter project, copied manually into `extracts_ttps/` — see
[`extracts_ttps/README.md`](extracts_ttps/README.md) for details.

### Statistical analysis (`dataset_analysis/`)

Reads a CSV built from `extracts_ttps/dataset_completo_limpio.json` and
generates descriptive plots and summaries: TTP frequency, TTPs per
document, IoC frequency and type, IoC/TTP co-occurrence, etc.

**Note:** this repository does not currently include a script that
converts `dataset_completo_limpio.json` into the CSV consumed by this
phase (`output_dataset_limpio_v2.csv`). It must be generated manually
(e.g. with `pandas.json_normalize`) before running this phase — see
[`dataset_analysis/README.md`](dataset_analysis/README.md) for a starting
example.

## Prerequisites summary

- Conda or Miniconda, Python 3.10+
- [LM Studio](https://lmstudio.ai/) running locally with the
  `lmstudio-community/Qwen2-VL-7B-Instruct-GGUF` model loaded, exposing an
  OpenAI-compatible API at `http://localhost:1234/v1` (required for Phase 2)
- `label_dict.pkl` and `ttp_id_name.pkl` from the
  [TTPXHunter](https://github.com/dessertlab/TTPXHunter) project, placed
  manually into `extracts_ttps/` (required for Phase 4)
- A CUDA-capable GPU is recommended (but not required) for Phase 4 — it
  falls back to CPU automatically
- Each phase folder has its own conda `environment.yml` (or, for
  `Conversion_TXT/`, `conversion_txt.yml`) with the exact dependencies for
  that phase; see each folder's `README.md`

## Running the full pipeline

1. Collect PDF reports into `Conversion_TXT/ReportsA|B|C|CTI_HAL/` (Phase 1).
2. Run `Conversion_TXT/main.py` once per batch, with LM Studio running
   (Phase 2).
3. Run `Clean_duplicated/audit_files.py` (Phase 3).
4. Place `label_dict.pkl`/`ttp_id_name.pkl` into `extracts_ttps/`, then run
   `extracts_ttps/process_files.py` followed by
   `extracts_ttps/clean_dataset.py` (Phases 4, 5, 6).
5. Generate `output_dataset_limpio_v2.csv` from
   `extracts_ttps/dataset_completo_limpio.json` and place it in
   `extracts_ttps/`, then run
   `dataset_analysis/analisis_ttp_dataset_vEnrique.py` (statistical
   analysis).

Each step's detailed instructions, inputs and outputs are documented in
that folder's own `README.md`.
