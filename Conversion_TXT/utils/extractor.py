import fitz
import os
import io
import re
from pathlib import Path
from PIL import Image


def clean_text(text):
    """
    Normalizes whitespace while preserving line breaks, to improve readability.
    """
    cleaned_lines = []
    for line in text.splitlines():
        normalized_line = re.sub(r'[ \t]+', ' ', line).strip()
        if normalized_line:
            cleaned_lines.append(normalized_line)
    return "\n".join(cleaned_lines)


def extract_text_with_refs(doc, image_map, page_num):
    """
    Links extracted images to their visual position in the text for a specific page.
    """
    page_content = ""
    page = doc[page_num]

    page_items = []

    # 1. Get text blocks
    for block in page.get_text("blocks"):
        # Clean the block text, normalizing whitespace
        cleaned_text = clean_text(block[4])
        if cleaned_text:  # Only add if not empty
            page_items.append({
                "type": "text",
                "top": block[1],
                "content": cleaned_text
            })

    # 2. Get image rectangles
    image_list = page.get_images(full=True)
    for img_index, img in enumerate(image_list):
        xref = img[0]
        if (page_num, img_index) in image_map:
            img_id = image_map[(page_num, img_index)]
            # Find where this image is drawn
            rects = page.get_image_rects(xref)
            for rect in rects:
                page_items.append({
                    "type": "image",
                    "top": rect.y0,
                    "content": f"[{img_id}]"
                })

    # 3. Sort by Y coordinate (top to bottom)
    page_items.sort(key=lambda x: x["top"])

    # Build the page content, keeping line breaks for readability
    page_lines = [f"--- Page {page_num + 1} ---"]
    for item in page_items:
        page_lines.append(item["content"])

    page_content = clean_text("\n".join(page_lines))

    return page_content


def save_images_by_page(doc, output_folder):
    """
    Extracts every image instance from the PDF and saves them in page-specific folders.
    Returns a map of (page_index, image_index) to IMAGE_X ID.
    """
    os.makedirs(output_folder, exist_ok=True)
    image_map = {}  # Key: (page_index, img_index), Value: IMAGE_ID
    global_counter = 0

    for page_index in range(len(doc)):
        image_list = doc.get_page_images(page_index)

        for img_index, img in enumerate(image_list):
            xref = img[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # Use Pillow to ensure the image is a valid, openable PNG
                image = Image.open(io.BytesIO(image_bytes))

                global_counter += 1
                img_id = f"IMAGE_{global_counter}"

                # Create page-specific folder
                page_folder = os.path.join(output_folder, f"page_{page_index + 1}")
                os.makedirs(page_folder, exist_ok=True)

                filename = f"{img_id}.png"
                image.save(os.path.join(page_folder, filename), "PNG")

                # Map this specific instance on this page
                image_map[(page_index, img_index)] = img_id
            except Exception as e:
                print(f"Could not extract image {xref} on page {page_index}: {e}")
                continue

    return image_map


def extract_cti_from_pdf(pdf_path, pdf_processed_dir):
    """
    Extracts text and images from a PDF, saving them in a structured output folder
    with separate subfolders for each page's text and images.
    All line breaks are normalized in the output text files.

    input:
        pdf_path (str): Path to the PDF file to be processed.
        pdf_processed_dir (str | Path): Absolute path to the shared
            "pdf_processed" folder (Conversion_TXT/pdf_processed) where the
            per-PDF output folder will be created.
    output:
        output_folder (str): Path to the folder where extracted text and
            images were saved.
    """
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_folder = str(Path(pdf_processed_dir) / f"{base_name}_output")

    # Create main output folder
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Create main images folder
    images_folder = os.path.join(output_folder, "images")
    if not os.path.exists(images_folder):
        os.makedirs(images_folder)

    # Open the PDF document
    doc = fitz.open(pdf_path)
    print(f"Extracting images from {pdf_path}...")

    # Extract all images and save them in page-specific folders
    image_map = save_images_by_page(doc, images_folder)

    print("Reconstructing text with anchors for each page (removing line breaks)...")

    # Create a folder for text files
    text_folder = os.path.join(output_folder, "text")
    os.makedirs(text_folder, exist_ok=True)

    # Process each page individually
    all_page_texts = []
    for page_num in range(len(doc)):
        print(f"Processing page {page_num + 1}...")

        # Extract text with references for this page (without line breaks)
        page_text = extract_text_with_refs(doc, image_map, page_num)

        # Store for full document
        all_page_texts.append(page_text)

        # Save individual page text file (without line breaks)
        page_text_path = os.path.join(text_folder, f"page_{page_num + 1}.txt")
        with open(page_text_path, "w", encoding="utf-8") as f:
            f.write(page_text)

    # Save complete raw text file inside the PDF output folder
    full_text = "\n\n".join(all_page_texts)
    full_text = clean_text(full_text)

    report_text_path = os.path.join(output_folder, f"{base_name}_raw.txt")
    with open(report_text_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    doc.close()

    print(f"\nExtraction complete!")
    print(f"Main output folder: {output_folder}")
    print(f"Text files saved in: {text_folder}")
    print(f"Image files saved in: {images_folder}")
    print(f"Each page has its own folder under 'images/' with its corresponding images")
    print(f"\nGenerated files:")
    print(f"  - Individual pages: {text_folder}/page_X.txt")
    print(f"  - Full raw text: {report_text_path}")

    return output_folder


# Additional function to clean up existing text files
def clean_existing_text_files(output_folder):
    """
    Removes stray line breaks from text files that were already generated.
    Useful if you already have generated files and want to clean them up.
    """
    text_folder = os.path.join(output_folder, "text")
    if not os.path.exists(text_folder):
        print(f"Folder not found: {text_folder}")
        return

    print(f"Cleaning text files in {text_folder}...")

    # Clean per-page files
    for page_file in os.listdir(text_folder):
        if page_file.startswith("page_") and page_file.endswith(".txt"):
            file_path = os.path.join(text_folder, page_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            cleaned_content = clean_text(content)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

            print(f"  Cleaned: {page_file}")

    # Clean txt files at the root of the output folder
    for file_name in os.listdir(output_folder):
        if file_name.endswith(".txt"):
            file_path = os.path.join(output_folder, file_name)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            cleaned_content = clean_text(content)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

            print(f"  Cleaned: {file_name}")

    print("Cleanup complete.")
