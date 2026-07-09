"""
clean_dataset.py - Dataset cleanup utility (duplicate of extracts_ttps/clean_dataset.py).

Kept in this folder for convenience so the statistical analysis workflow
(dataset_analysis/) can be run standalone. It reads/writes the dataset JSON
directly inside extracts_ttps/, where "the dataset" of the pipeline lives.

Removes TTP entries whose "context" field is actually a failed/empty image
transcription (e.g. "This image is blank...") rather than real report text.

All paths are computed from this file's own location
(Path(__file__).resolve()), so the script can be run from any computer
without editing hardcoded paths, as long as the project folder layout is
preserved.
"""

import json
from pathlib import Path

DATASET_ANALYSIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DATASET_ANALYSIS_DIR.parent
EXTRACTS_DIR = PROJECT_ROOT / "extracts_ttps"

# Default input/output files, both inside extracts_ttps/ (where the dataset lives).
DEFAULT_INPUT_FILE = EXTRACTS_DIR / "dataset_completo.json"
DEFAULT_OUTPUT_FILE = EXTRACTS_DIR / "dataset_completo_limpio.json"

# Exact phrases to search for and remove (in the "context" field).
# These are typical "no useful content" answers returned by the
# vision-language model when an image has no transcribable text.
PHRASES_TO_REMOVE = [
    "The payload itself was disguised as a PNG file in an attempt to resemble the",
    "There are no discernible words, numbers, or symbols present in this image.",
    "There are no discernible words or characters present in this image.",
    "There are no discernible words, numbers, or symbols present in this image.",
    "The text is not visible in the provided image.",
    "The text in the image is not visible due to the nature of the image content.",
    "This image is completely blank and does not contain any visible text.",
    "This image is blank and does not contain any visible text.",
    "The image is blank and contains no visible text.",
    "The image is completely blank and does not contain any visible text.",
    "The image is blank and does not contain any visible text.",
    "The image is blank and does not contain any text to transcribe.",
    "This image is blank and does not contain any visible text to transcribe.",
    "The image is blank and does not contain any visible text to transcribe.",
    "The image is completely blank and does not contain any visible text to transcribe.",
    "The text is empty and does not contain any visible text to transcribe.",
    "This is a blank yellow background with no text or other content visible.",
    "The text is empty and does not contain any visible characters.",
    "The text is empty and does not contain any characters.",
    "The image appears to be a green wax seal with no discernible text or symbols on it.",
    "The text appears to be a mix of random characters and some recognizable words.",
    "The background is plain and does not contain any visible text or logos.",
    "The text in the image is not visible due to the nature of the image content.",
    "The text in the image is not clear and appears to be a random assortment of characters.",
    "The image is entirely red and does not contain any discernible text or content.",
    "The image is entirely red and does not contain any visible text.",
    "The image is entirely red and does not contain any discernible text or content to transcribe.",
    "The text is not clear and cannot be transcribed accurately.",
    "There is no visible text or code within this image.",
    "There are no other visible text or elements within this image.",
    "The text in the image is not clear and appears to be a random assortment of characters.",
    "The text is too small and blurry to be transcribed accurately.",
    "The text in the image is not visible due to the nature of the content being an image of a person working in a server room.",
    "There are no visible texts or codes in this image.",
    "The image is blurred and indistinct, making it impossible to transcribe any visible text.",
    "The image appears to be a blue and white abstract design with no discernible text or recognizable content.",
    "The text seems to be partially obscured and unreadable.",
    "The image appears to be a blue and white abstract design with no discernible text or recognizable content.",
    "The image is entirely red and does not contain any text to transcribe.",
    "The image is empty and does not contain any text to transcribe.",
    "The image is a black and white pattern that appears to be a series of squares arranged in a grid.",
    "The background color transitions smoothly from the center to the edges, creating a gradient effect.",
    "There is no discernible text or additional content within the image.",
    "The image appears to be a placeholder or a generic background with no discernible text.",
    "There are no visible texts, numbers, or other discernible information within this image.",
    "The image appears to be a placeholder or a generic blue circle without any visible text.",
    "The text is completely obscured and unreadable due to the high level of noise and distortion in the image.",
    "The text in the image is not clear and appears to be a series of random characters.",
    "The image appears to be a series of blue and black horizontal lines with no discernible text or patterns.",
    "There are no visible text lines or codes within this image.",
    "This image is a blank white background with no visible text, logos, IP addresses, or code.",
    "This image is completely white and lacks any discernible text, logos, IP addresses, or code.",
    "The image appears to be a random assortment of characters and symbols, with no discernible pattern or meaning.",
    "There are no visible texts, numbers, or other characters within this image.",
    "There are no discernible words or text within the image.",
    "The image appears to be a digital representation of a spiral pattern with varying shades of blue and white.",
    "The image is a colorful abstract design with no discernible text or recognizable content.",
    "The image is entirely orange and does not contain any discernible text or content to transcribe.",
    "The image appears to be a pattern of horizontal lines with varying shades and colors.",
    "The image appears to be a pattern of horizontal lines with varying intensities and colors.",
    "The image appears to be a pattern of horizontal lines with varying shades of gray and black.",
    "The background is plain and does not contain any visible text.",
    "There are no other visible text elements within the image.",
    "The background is blurred with shades of blue and green, giving it a moody, atmospheric feel.",
    "The image appears to be a complex diagram with various lines and nodes connected by arrows.",
    "There are no discernible words or text within this image.",
    "The image is empty and does not contain any visible text to transcribe.",
    "The text in the image is not clear and appears to be a series of vertical lines.",
    "The text in the image is not clear and appears to be a series of black and white lines without any discernible characters or words.",
    "The image is a long, horizontal line of text that appears to be a series of random characters and numbers.",
    "The text is not readable due to the presence of a barcode and other visual obstructions.",
    "This image is blank and contains no visible text.",
    "The text in the image is not clear and appears to be a series of horizontal lines with no discernible characters or words.",
    "The text is not readable due to the presence of horizontal lines and a striped pattern.",
    "The text is not readable due to the presence of horizontal lines and a pink background.",
    "The text is not readable due to the presence of a barcode and other obstructions.",
    "The text is not readable due to the presence of a barcode and other non-text elements in the image.",
    "The text in the image is not clear and appears to be a series of vertical lines.",
    "The image is empty and does not contain any visible text to transcribe.",
    "The text in the image appears to be blank and does not contain any visible characters that can be transcribed.",
    "There is no discernible text that can be transcribed from this image.",
    "There is no discernible text to transcribe.",
    "There are no visible lines of text in this image.",
    "There are no discernible words or characters in this image.",
    "The text is not readable due to the presence of horizontal lines and color bars.",
    "The image is empty and does not contain any visible text to transcribe.",
    "The document itself is blank.",
    "The text in the image is blank and does not contain any visible text to transcribe.",
    "The image is empty and does not contain any visible text to transcribe.",
    "It appears to be a blank space with some blue coloration.",
    "The image provided does not contain any text that can be transcribed.",
    "There are no additional texts or elements visible within this image.",
    "The image is entirely blank and does not contain any visible text.",
    "The image appears to be a dark background with blue lines and dots, but no discernible text can be transcribed from it.",
    "The text transcribed from the image is: ",
    "There are no visible lines of text in this image.",
    "The image is a series of horizontal lines with no discernible text or characters.",
    "The image appears to be a pattern of vertical lines with varying colors and shades.",
    "The text is not readable due to the presence of horizontal lines and a pink background.",
    "The image appears to be a pattern of vertical lines with varying colors and shades.",
    "The image is a blank and does not contain any visible text to transcribe.",
    "There are no discernible words or characters in this image.",
    "The text is not readable due to the presence of horizontal lines and a gradient background.",
    "The text in the image is not clear and appears to be a series of vertical lines.",
    "There are no visible lines of text in this image.",
    "The image is a blank gray background with no visible text, logos, IP addresses, or code.",
    "The text is not readable due to the presence of lines and characters that obscure it.",
    "The text is not readable due to the presence of horizontal lines and a vertical bar.",
    "The image is entirely composed of horizontal lines with no discernible text or content.",
    "The text in the image is not clear and appears to be a series of black and white lines without any discernible characters or words.",
    "There is no discernible text to transcribe.",
    "The text is not readable due to the presence of a barcode and other non-text elements in the image.",
    "This image is blank and contains no text.",
    "This image is blank and does not contain any text to transcribe.",
    "The text appears to be blank or contains no visible characters.",
    "The text appears to be blank and does not contain any visible characters.",
    "The text in the image is not clear and appears to be a series of vertical lines with no discernible characters or words.",
    "This image is blank and does not contain any text to transcribe.",
    "The image appears to be a colorful abstract composition with shades of pink and purple.",
    "The text in the image is in Arabic and appears to be a continuous block of text without any visible breaks or formatting.",
    "The image appears to be a green circular icon with no discernible text or symbols within it.",
    "The image is entirely red with no discernible text or content to transcribe.",
    "The text in the image appears to be a series of random characters and numbers, which do not form any recognizable words or phrases."
]


def clean_dataset_entries(input_file: Path, output_file: Path) -> None:
    """
    Reads the JSON array of files, looks inside each file's "ttps" list for
    the "context" field, and removes every TTP entry that contains one of
    the forbidden phrases.
    """
    try:
        print("Reading JSON file...")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total_files = len(data)
        total_ttps_before = 0
        total_ttps_after = 0
        total_ttps_removed = 0

        print(f"Total files: {total_files}")

        for entry in data:
            if 'ttps' in entry:
                ttps_before = len(entry['ttps'])
                total_ttps_before += ttps_before

                filtered_ttps = []
                for ttp in entry['ttps']:
                    context = ttp.get('context', '')
                    contains_forbidden_phrase = False
                    for phrase in PHRASES_TO_REMOVE:
                        if phrase in context:
                            contains_forbidden_phrase = True
                            total_ttps_removed += 1
                            break

                    if not contains_forbidden_phrase:
                        filtered_ttps.append(ttp)

                entry['ttps'] = filtered_ttps
                ttps_after = len(filtered_ttps)
                total_ttps_after += ttps_after

                if 'metadata' in entry:
                    entry['metadata']['total_ttps_detected'] = ttps_after

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"Clean file created: {output_file}")
        print(f"Total TTPs before: {total_ttps_before}")
        print(f"Total TTPs after: {total_ttps_after}")
        print(f"TTPs removed: {total_ttps_removed}")

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    clean_dataset_entries(DEFAULT_INPUT_FILE, DEFAULT_OUTPUT_FILE)
