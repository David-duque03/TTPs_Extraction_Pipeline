import os
import re
import base64
from pathlib import Path
from openai import OpenAI


def qwuen2_image_translation(output_folder, txt_out_dir):
    """
    Processes images using Qwen2-VL for OCR and integrates the results into the text.
    Compatible with page-structured folders.

    input:
        output_folder (str): Path to the folder containing images and text files
            for a single PDF (created by extract_cti_from_pdf).
        txt_out_dir (str | Path): Absolute path to the shared folder where the
            final, per-report TXT file (with image transcriptions applied)
            will be exported.
    output:
        output_text_folder (str): folder with enriched text files, where image
            tags have been replaced by their transcriptions, for each page.
    """
    # LM Studio configuration
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    MODEL_VL = "lmstudio-community/Qwen2-VL-7B-Instruct-GGUF"

    def encode_image(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def transcribe_image(path):
        """
        Uses the VL model to perform a literal transcription (OCR) of the image content.
        """
        try:
            b64 = encode_image(path)
            response = client.chat.completions.create(
                model=MODEL_VL,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "OCR MODE: Transcribe all visible text in this image line by line. "
                                    "Do not describe the colors or shapes. Just output the literal text found. "
                                    "If there are logs, IP addresses, or code, copy them exactly as they appear."
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    ]
                }],
                temperature=0.0, # temperature 0 for higher fidelity and less 'creativity'
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error transcribing {os.path.basename(path)}: {e}"

    # Define folder paths
    text_folder = os.path.join(output_folder, "text")
    images_folder = os.path.join(output_folder, "images")
    output_text_folder = os.path.join(output_folder, "text_with_transcriptions")

    # Create output folder for transcribed texts
    os.makedirs(output_text_folder, exist_ok=True)

    # Check if folders exist
    if not os.path.exists(text_folder):
        print(f"Error: Text folder not found at {text_folder}")
        return

    if not os.path.exists(images_folder):
        print(f"Error: Images folder not found at {images_folder}")
        return

    # Get all page text files
    page_files = [f for f in os.listdir(text_folder) if f.startswith("page_") and f.endswith(".txt")]
    page_files.sort(key=lambda x: int(re.search(r'page_(\d+)', x).group(1)))

    print(f"Found {len(page_files)} page files to process")

    # Process each page file
    all_transcriptions = []

    for page_file in page_files:
        page_num = re.search(r'page_(\d+)', page_file).group(1)
        page_path = os.path.join(text_folder, page_file)

        print(f"\nProcessing {page_file}...")

        # Read page content
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all image tags in this page
        tags = re.findall(r"\[IMAGE_(\d+)\]", content)
        unique_tags = sorted(set(tags), key=int)

        if unique_tags:
            print(f"  Found {len(unique_tags)} images to transcribe")

            # Process each image tag
            for tag_id in unique_tags:
                # Search for the image in all page folders
                img_found = False

                # Look in each page folder within the images directory
                for page_dir in os.listdir(images_folder):
                    page_dir_path = os.path.join(images_folder, page_dir)
                    if os.path.isdir(page_dir_path):
                        img_path = os.path.join(page_dir_path, f"IMAGE_{tag_id}.png")

                        if os.path.exists(img_path):
                            print(f"    > Transcribing IMAGE_{tag_id} from {page_dir}...")
                            transcription = transcribe_image(img_path)

                            # Replace the tag with the extracted text
                            replacement = f"{transcription}\n"
                            content = content.replace(f"[IMAGE_{tag_id}]", replacement)

                            img_found = True
                            all_transcriptions.append(f"Page {page_num}, IMAGE_{tag_id}:\n{transcription}\n")
                            break

                if not img_found:
                    print(f"    Warning: IMAGE_{tag_id}.png not found in any page folder")
                    content = content.replace(f"[IMAGE_{tag_id}]", "[IMAGE_NOT_FOUND]\n")
        else:
            print(f"  No images found in this page")

        # Save transcribed page to new folder
        output_page_path = os.path.join(output_text_folder, f"page_{page_num}_transcribed.txt")
        with open(output_page_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  Saved transcribed page to {output_page_path}")

    # Also create a consolidated file with all transcriptions
    if all_transcriptions:
        consolidated_path = os.path.join(output_folder, "all_transcriptions.txt")
        with open(consolidated_path, "w", encoding="utf-8") as f:
            f.write("\n".join(all_transcriptions))
        print(f"\nConsolidated transcriptions saved to: {consolidated_path}")

    # Optionally create a full document with all transcribed pages
    full_document = []
    for page_file in sorted(os.listdir(output_text_folder)):
        if page_file.endswith("_transcribed.txt"):
            with open(os.path.join(output_text_folder, page_file), "r", encoding="utf-8") as f:
                full_document.append(f.read())

    if full_document:
        full_doc_path = os.path.join(output_folder, "full_document_transcribed.txt")
        full_doc_text = "\n".join(full_document)
        with open(full_doc_path, "w", encoding="utf-8") as f:
            f.write(full_doc_text)
        print(f"Full document with transcriptions saved to: {full_doc_path}")

        # Export the final transcribed TXT to the shared txt_out_<batch> folder
        base_name = os.path.basename(output_folder)
        if base_name.endswith("_output"):
            base_name = base_name[:-7]

        txt_out_folder = str(Path(txt_out_dir))
        os.makedirs(txt_out_folder, exist_ok=True)
        final_txt_path = os.path.join(txt_out_folder, f"{base_name}.txt")

        with open(final_txt_path, "w", encoding="utf-8") as f:
            f.write(full_doc_text)

        print(f"Final TXT exported to: {final_txt_path}")

    print(f"\nTranscription of images completed. Results saved in: {output_text_folder}")
    return output_text_folder
