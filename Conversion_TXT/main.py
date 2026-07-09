# Phase 2 - PDF to TXT conversion (entry point)
#
# Environment setup:
#   conda activate conversion_txt
#
# External requirement:
#   LM Studio must be running locally and serving the vision-language model:
#   lmstudio-community/Qwen2-VL-7B-Instruct-GGUF - http://localhost:1234/v1
#
# This script converts every PDF report found in one "ReportsX" subfolder
# into plain text, transcribing embedded images/screenshots with Qwen2-VL.
# All paths below are computed from this file's own location, so the
# pipeline can be run from any computer without editing hardcoded paths,
# as long as the folder layout of the project is preserved.

import os
from pathlib import Path

from utils.extractor import extract_cti_from_pdf
from utils.qwen2_image import qwuen2_image_translation

# =========================================================================
# CONFIGURATION
# =========================================================================

# Name of the reports subfolder to process in this run.
# Change this value to switch between report batches and re-run the script:
#   "ReportsA" | "ReportsB" | "ReportsC" | "ReportsCTI_HAL"
REPORTS_FOLDER_NAME = "ReportsCTI_HAL"

# Absolute path of the folder containing this script (Conversion_TXT/).
# Using __file__ instead of the current working directory makes the script
# portable: it always resolves paths relative to the project structure,
# regardless of which computer or directory it is launched from.
CONVERSION_DIR = Path(__file__).resolve().parent

# Input: original PDF reports for the selected batch.
INPUT_DIR = CONVERSION_DIR / REPORTS_FOLDER_NAME

# Intermediate output: per-PDF extracted text/images (Phase 2 raw output).
# Shared by every batch, as in the original layout.
PDF_PROCESSED_DIR = CONVERSION_DIR / "pdf_processed"

# Final output: one shared TXT file per report, named after the batch
# (txt_out_A, txt_out_B, txt_out_C, txt_out_CTI_HAL), matching the existing
# naming convention already used in this project.
_suffix = REPORTS_FOLDER_NAME.replace("Reports", "", 1)
TXT_OUT_DIR = CONVERSION_DIR / f"txt_out_{_suffix}"


def find_pdf_files(base_folder: Path) -> list[str]:
    """Recursively finds every .pdf file under base_folder."""
    return sorted(
        os.path.join(root, file_name)
        for root, _, files in os.walk(base_folder)
        for file_name in files
        if file_name.lower().endswith(".pdf")
    )


def main():
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Reports folder not found: {INPUT_DIR}")

    PDF_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    TXT_OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Reports folder:        {INPUT_DIR}")
    print(f"PDF processed folder:  {PDF_PROCESSED_DIR}")
    print(f"TXT output folder:     {TXT_OUT_DIR}")

    all_pdf_paths = find_pdf_files(INPUT_DIR)
    total_pdfs = len(all_pdf_paths)
    print(f"Total PDF files found: {total_pdfs}")

    for count, pdf_path in enumerate(all_pdf_paths, start=1):
        print(f"Processing PDF {count}/{total_pdfs}: {pdf_path}")
        output_folder = extract_cti_from_pdf(pdf_path, PDF_PROCESSED_DIR)
        qwuen2_image_translation(output_folder, TXT_OUT_DIR)


if __name__ == "__main__":
    main()
