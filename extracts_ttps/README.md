# extracts_ttps (Phases 4, 5 and 6 — TTP extraction, IoC extraction, dataset build)

This module runs the TTPXHunter model over the deduplicated, English-only
reports to detect MITRE ATT&CK techniques (Phase 4), scans the same text for
indicators of compromise via regular expressions (Phase 5), and merges both
results into a single structured JSON dataset (Phase 6). This is where "the
dataset" of the pipeline is produced and stored, as described in the
project's root `README.md`.

## Folder layout

```
extracts_ttps/
├── process_files.py          # Phases 4 + 5 + 6: builds dataset_completo.json
├── clean_dataset.py           # Phase 6 cleanup: removes noisy OCR "context" entries
├── label_dict.pkl             # TTPXHunter label mapping (place it here manually)
├── ttp_id_name.pkl            # TTPXHunter technique-id -> name mapping (place it here manually)
├── dataset_completo.json         # Output of process_files.py
├── dataset_completo_limpio.json  # Output of clean_dataset.py
└── environment.yml
```

All paths are computed at runtime from each script's own location
(`Path(__file__).resolve().parent`), so the project can be moved to any
computer/drive and still work, as long as the folder layout is preserved.

## Input

`process_files.py` reads every `.txt` file from:

```
Clean_duplicated/TXT_dedup/
```

which is the output of Phase 3. Make sure that folder has already been
generated (see `Clean_duplicated/README.md`) before running this phase.

## Requirements

- Conda or Miniconda
- Python 3.10+
- A CUDA-capable GPU is recommended but not required (the script falls back
  to CPU automatically via `torch.cuda.is_available()`)
- `label_dict.pkl` and `ttp_id_name.pkl` from the
  [TTPXHunter](https://github.com/dessertlab/TTPXHunter) project, copied
  into this folder

## Installation

```bash
conda env create -f environment.yml
conda activate extracts_ttps
```

The first run will also download the `nanda-rani/TTPXHunter` model weights
from Hugging Face and the NLTK `punkt_tab` tokenizer data.

## Usage

From this folder, after Phase 3 has produced `Clean_duplicated/TXT_dedup/`:

```bash
python process_files.py
```

This generates `dataset_completo.json`, with one entry per report:

```json
{
  "file_name": "<report>.txt",
  "metadata": {
    "source": "TEXT",
    "iocs": { "ips": [...], "md5": [...], "sha1": [...], "sha256": [...], "urls": [...] },
    "total_ttps_detected": 0
  },
  "ttps": [
    {
      "context": "sentence text",
      "technique": "T1059",
      "metadata": { "page_number": 1, "technique_name": "Command and Scripting Interpreter" }
    }
  ]
}
```

Optionally, clean up entries whose "context" is a failed image transcription
(e.g. "This image is blank...") rather than real report text:

```bash
python clean_dataset.py
```

This produces `dataset_completo_limpio.json`, used as the input for the
statistical analysis phase (`dataset_analysis/`).

## Configuration

Both scripts default to reading/writing files inside this same folder. If
you need to point them at different files, edit the constants at the top of
each script (`BASE_DIR`, `OUTPUT_FILE` in `process_files.py`;
`DEFAULT_INPUT_FILE`, `DEFAULT_OUTPUT_FILE` in `clean_dataset.py`), or call
`clean_dataset_entries(input_file, output_file)` directly from another
script.
