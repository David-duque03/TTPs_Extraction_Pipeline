# dataset_analysis (Statistical analysis phase)

This module reads the cleaned TTP/IoC dataset produced by `extracts_ttps/`
and generates the descriptive statistics, plots, and CSV summaries used to
analyze the pipeline's final results: TTP frequency, TTPs per document, IoC
frequency and type, IoC/TTP co-occurrence across documents, and related
figures.

## Folder layout

```
dataset_analysis/
├── analisis_ttp_dataset_vEnrique.py   # Main analysis script (plots + summaries)
├── clean_dataset.py                    # Convenience copy of extracts_ttps/clean_dataset.py
├── environment.yml
├── plots_iocs_enrique/                 # Output plots (created automatically)
└── plots_new_iocs_filtered/            # Output plots, filtered variant (created automatically)
```

All paths are computed at runtime from each script's own location
(`Path(__file__).resolve().parent`), so the project can be moved to any
computer/drive and still work, as long as the folder layout is preserved.

## Input

`analisis_ttp_dataset_vEnrique.py` reads a CSV file from:

```
extracts_ttps/output_dataset_limpio_v2.csv
```

**Important:** this repository does not currently include a script that
converts the JSON dataset (`extracts_ttps/dataset_completo_limpio.json`,
the output of Phase 6) into this CSV. You need to generate it yourself
before running the analysis, for example with pandas:

```python
import json
import pandas as pd
from pathlib import Path

with open("extracts_ttps/dataset_completo_limpio.json", encoding="utf-8") as f:
    data = json.load(f)

df = pd.json_normalize(data)
df.to_csv("extracts_ttps/output_dataset_limpio_v2.csv", index=False)
```

The exact normalization/flattening logic (how the nested `ttps` and
`metadata.iocs` fields are expanded into columns) depends on what
`analisis_ttp_dataset_vEnrique.py` expects to find in the CSV — review the
`parse_complex_data` helper and the column names used throughout the script
(e.g. `ttps_por_doc`, `iocs_por_doc`, `coinc_df`, `ttp_label`) before writing
your conversion step, and adapt it if your CSV columns differ.

Make sure Phase 6 (`extracts_ttps/`, see its `README.md`) has already been
run and has produced `dataset_completo_limpio.json` before generating this
CSV.

## Requirements

- Conda or Miniconda
- Python 3.10+

## Installation

```bash
conda env create -f environment.yml
conda activate dataset_analysis
```

## Usage

From this folder, after the CSV described above has been placed at
`extracts_ttps/output_dataset_limpio_v2.csv`:

```bash
python analisis_ttp_dataset_vEnrique.py
```

This prints descriptive statistics to the console and saves plots into:

```
plots_iocs_enrique/
plots_new_iocs_filtered/
```

Both folders are created automatically if they don't exist.

### clean_dataset.py

This folder also contains a convenience copy of `extracts_ttps/clean_dataset.py`,
so the cleanup step can be re-run from here without switching folders. It
reads/writes files directly inside `extracts_ttps/`
(`dataset_completo.json` -> `dataset_completo_limpio.json`), not locally:

```bash
python clean_dataset.py
```

## Configuration

If you need to point the analysis script at a different CSV file or output
folders, edit the constants at the top of `analisis_ttp_dataset_vEnrique.py`
(`csv_path`, `PLOTS_DIR`, `PLOTS_FILTERED_DIR`).
