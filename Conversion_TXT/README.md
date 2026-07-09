# Conversion_TXT (Phase 2 — PDF to TXT conversion)

Converts the PDF reports collected in Phase 1 into plain text, including
transcription of embedded images/screenshots with Qwen2-VL running locally
in LM Studio. This is Phase 2 of the TTP extraction pipeline (see the
project's root `README.md` for the full pipeline overview).

## Folder layout

```
Conversion_TXT/
├── ReportsA/            # Input PDFs, batch A
├── ReportsB/            # Input PDFs, batch B
├── ReportsC/            # Input PDFs, batch C
├── ReportsCTI_HAL/      # Input PDFs, CTI-HAL batch
├── pdf_processed/       # Phase 2 raw output, shared by every batch
│   └── <pdf_name>_output/
├── txt_out_A/            # Final TXT files for batch A
├── txt_out_B/            # Final TXT files for batch B
├── txt_out_C/            # Final TXT files for batch C
├── txt_out_CTI_HAL/      # Final TXT files for the CTI-HAL batch
├── utils/
│   ├── extractor.py       # Extracts text and images from each PDF
│   └── qwen2_image.py     # Performs OCR/image transcription
├── main.py                 # Runs the pipeline
└── conversion_txt.yml       # Recommended conda environment
```

All input/output paths are computed at runtime from this script's own
location (`Path(__file__).resolve().parent`), so the project can be moved to
any computer/drive and still work, as long as the folder layout above is
preserved.

## Flow

1. Finds every `.pdf` file inside the selected `ReportsX/` subfolder (recursive).
2. Extracts text and images per page.
3. Inserts `[IMAGE_X]` anchors in the text at the position where each image appears.
4. Transcribes each image with Qwen2-VL (OCR mode).
5. Generates per-page TXT files and a final TXT per document.

## Requirements

- Python 3.10+
- LM Studio running at `http://localhost:1234/v1`
- Loaded model: `lmstudio-community/Qwen2-VL-7B-Instruct-GGUF`

## Installation

```bash
conda env create -f conversion_txt.yml
conda activate conversion_txt
```

## Configuration

Open `main.py` and set `REPORTS_FOLDER_NAME` to the batch you want to
process before each run:

```python
REPORTS_FOLDER_NAME = "ReportsCTI_HAL"  # "ReportsA" | "ReportsB" | "ReportsC" | "ReportsCTI_HAL"
```

Every other path (`pdf_processed/`, `txt_out_<batch>/`) is derived
automatically from this value and from the script's location — nothing else
needs to be edited.

## Usage

Make sure LM Studio is running with the model loaded, then, from this
folder:

```bash
python main.py
```

Repeat once per batch (changing `REPORTS_FOLDER_NAME` each time) until all
`ReportsA`, `ReportsB`, `ReportsC` and `ReportsCTI_HAL` folders have been
processed.

## Output

For each PDF, the pipeline creates `pdf_processed/<pdf_name>_output/` with:

- `text/page_N.txt`
- `images/page_N/IMAGE_X.png`
- `text_with_transcriptions/page_N_transcribed.txt`
- `all_transcriptions.txt`
- `full_document_transcribed.txt`
- `<pdf_name>_raw.txt`

The final TXT file for each input PDF (with image transcriptions applied) is
saved in the batch's shared output folder:

- `txt_out_<batch>/<pdf_name>.txt`

These `txt_out_*` folders are the input consumed by Phase 3 (`Clean_duplicated/`).

## Note

If LM Studio is not running or the model is not loaded, image transcription
will fail for that PDF (the text extraction itself will still succeed).

## Execution Scheme (Functions + Libraries)

```text
INPUT PDF (ReportsX/*.pdf)
	|
	| main.py
	| - os.walk, os.path.join, str.endswith
	v
extract_cti_from_pdf(pdf_path, pdf_processed_dir)  [utils/extractor.py]
	| Libraries: fitz (PyMuPDF), os, io, re, pathlib, PIL.Image
	|
	|-- fitz.open(pdf_path)  -> open PDF document
	|-- save_images_by_page(doc, images_folder)
	|     - doc.get_page_images(page_index)
	|     - doc.extract_image(xref)
	|     - Image.open(BytesIO(...))
	|     - image.save(...)
	|     => OUTPUT: images/page_N/IMAGE_X.png
	|
	|-- extract_text_with_refs(doc, image_map, page_num)
	|     - page.get_text("blocks")
	|     - page.get_images(full=True)
	|     - page.get_image_rects(xref)
	|     - clean_text(...)
	|     => OUTPUT: text/page_N.txt (with [IMAGE_X] anchors)
	|
	|-- write raw full-document file
	|     - pdf_processed/<pdf_name>_output/<pdf_name>_raw.txt
	v
qwuen2_image_translation(output_folder, txt_out_dir)  [utils/qwen2_image.py]
	| Libraries: openai.OpenAI, os, re, base64, pathlib
	|
	|-- encode_image(path)
	|     - open(..., "rb")
	|     - base64.b64encode(...)
	|
	|-- transcribe_image(path)
	|     - client.chat.completions.create(...)
	|     - model: Qwen2-VL via LM Studio
	|
	|-- page processing loop
	|     - read text/page_N.txt
	|     - find [IMAGE_X] tags with regex
	|     - replace each tag with OCR text
	|     => OUTPUT: text_with_transcriptions/page_N_transcribed.txt
	|
	|-- consolidated outputs
	|     - all_transcriptions.txt
	|     - full_document_transcribed.txt
	|     - txt_out_<batch>/<pdf_name>.txt  (final exported TXT)
	v
FINAL TXT OUTPUT
```
