"""
process_files.py - Phases 4, 5 and 6 of the TTP extraction pipeline.

Phase 4: splits each report's text into sentences and classifies every
sentence with TTPXHunter, keeping the MITRE ATT&CK technique whenever the
model's confidence is above THRESHOLD.

Phase 5: scans the same text for indicators of compromise (IoCs) using
regular expressions (IPv4/IPv6 addresses, MD5/SHA1/SHA256 hashes and URLs).

Phase 6: merges the Phase 4 and Phase 5 results into a single JSON file,
structured per report (dataset_completo.json).

All paths are computed from this file's own location
(Path(__file__).resolve()), so the script can be run from any computer
without editing hardcoded paths, as long as the project folder layout is
preserved.
"""

import re
import json
import pickle
import torch
import nltk as n
from pathlib import Path
from transformers import RobertaTokenizer, RobertaForSequenceClassification

# =========================================================================
# CONFIGURATION - absolute paths derived from the project layout
# =========================================================================

EXTRACTS_DIR = Path(__file__).resolve().parent          # extracts_ttps/
PROJECT_ROOT = EXTRACTS_DIR.parent                       # pipeline_ttp_extraction/

# Input: deduplicated, English-only TXT reports produced by Phase 3.
BASE_DIR = PROJECT_ROOT / "Clean_duplicated" / "TXT_dedup"

# TTPXHunter label mappings. Place label_dict.pkl and ttp_id_name.pkl
# (downloaded from the TTPXHunter project) inside this folder.
LABEL_DICT_PATH = EXTRACTS_DIR / "label_dict.pkl"
TTPID2NAME_PATH = EXTRACTS_DIR / "ttp_id_name.pkl"

THRESHOLD = 0.9

# Output: structured JSON dataset for the whole corpus (Phase 6 output).
OUTPUT_FILE = EXTRACTS_DIR / "dataset_completo.json"

n.download("punkt_tab")

# =========================================================================
# MODEL LOADING
# =========================================================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = RobertaForSequenceClassification.from_pretrained("nanda-rani/TTPXHunter")
tokenizer = RobertaTokenizer.from_pretrained("nanda-rani/TTPXHunter")
model.to(device)
model.eval()


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def remove_consecutive_newlines(text: str) -> str:
    if not text:
        return ""
    cleaned_text = text[0]
    for char in text[1:]:
        if not (char == cleaned_text[-1] and cleaned_text[-1] == "\n"):
            cleaned_text += char
    return cleaned_text


def load_label_dict(label_dict_path: Path):
    with open(label_dict_path, "rb") as file:
        label_dict = pickle.load(file)
    return {v: k for k, v in label_dict.items()}


def load_ttpid_to_name_map(ttpid2name_path: Path):
    with open(ttpid2name_path, "rb") as file:
        return pickle.load(file)


def extract_ips_and_hashes(content: str):
    """Phase 5: extracts IoCs (IPs, hashes and URLs) via regular expressions."""
    ip_pattern = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    md5_pattern = r"\b[a-fA-F0-9]{32}\b"
    sha1_pattern = r"\b[a-fA-F0-9]{40}\b"
    sha256_pattern = r"\b[a-fA-F0-9]{64}\b"
    ip_v6_pattern = r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
    url_pattern = r"\bhttps?://[^\s/$.?#].[^\s]*\b"

    return {
        "ips": list(set(re.findall(ip_pattern, content) + re.findall(ip_v6_pattern, content))),
        "md5": list(set(re.findall(md5_pattern, content))),
        "sha1": list(set(re.findall(sha1_pattern, content))),
        "sha256": list(set(re.findall(sha256_pattern, content))),
        "urls": list(set(re.findall(url_pattern, content))),
    }


# =========================================================================
# TTP EXTRACTION (Phase 4)
# =========================================================================

def extract_ttps_from_sentences(sentences, inverted_label_dict, threshold=THRESHOLD):
    results = []

    for idx, text in enumerate(sentences):
        inputs = tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)

        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1)
        max_prob, predicted_class_indices = torch.max(probabilities, dim=1)

        if max_prob.item() > threshold:
            label_str = model.config.id2label[predicted_class_indices.item()]
            mapped_label = int(label_str.split("_")[1])

            if mapped_label in inverted_label_dict:
                ttp_id = inverted_label_dict[mapped_label]
                results.append(
                    {
                        "context": text,
                        "technique": ttp_id,
                        "page_number": idx + 1,
                    }
                )

    return results


# =========================================================================
# FILE PROCESSING
# =========================================================================

def process_file(filepath: Path, inverted_label_dict, ttpid_to_name_map):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
        text = file.read()

    text = remove_consecutive_newlines(text)
    text = text.replace("\t", " ").replace("\\'", "'")

    tokenized = n.sent_tokenize(text)
    sentences = []
    for sentence in tokenized:
        sentences.extend([line for line in sentence.split("\n") if len(line) > 0])

    ttp_results = extract_ttps_from_sentences(sentences, inverted_label_dict)
    iocs = extract_ips_and_hashes(text)

    ttps = []
    for item in ttp_results:
        technique_name = ttpid_to_name_map.get(item["technique"], "")
        ttps.append(
            {
                "context": item["context"],
                "technique": item["technique"],
                "metadata": {
                    "page_number": item["page_number"],
                    "technique_name": technique_name,
                },
            }
        )

    return {
        "file_name": filepath.name,
        "metadata": {
            "source": "TEXT",
            "iocs": iocs,
            "total_ttps_detected": len(ttps),
        },
        "ttps": ttps,
    }


# =========================================================================
# MAIN (Phase 6: merge results into the final dataset)
# =========================================================================

def main():
    if not BASE_DIR.exists():
        raise FileNotFoundError(
            f"Input folder not found: {BASE_DIR}\n"
            "Run Phase 3 (Clean_duplicated/audit_files.py) first."
        )

    inverted_label_dict = load_label_dict(LABEL_DICT_PATH)
    ttpid_to_name_map = load_ttpid_to_name_map(TTPID2NAME_PATH)

    all_results = []

    for file in sorted(BASE_DIR.glob("*.txt")):
        print(f"Processing: {file.name}")
        file_result = process_file(file, inverted_label_dict, ttpid_to_name_map)
        all_results.append(file_result)  # one entry per analyzed file

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)

    print(f"\nJSON generated: {OUTPUT_FILE}")
    print(f"Total files processed: {len(all_results)}")


if __name__ == "__main__":
    main()
