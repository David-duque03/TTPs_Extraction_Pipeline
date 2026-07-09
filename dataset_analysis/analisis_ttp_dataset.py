"""
analisis_ttp_dataset.py - Statistical analysis phase.

Reads the cleaned CSV version of the TTP/IoC dataset (produced from
extracts_ttps/dataset_completo_limpio.json) and generates the descriptive
plots and CSV summaries used for the statistical analysis of the pipeline's
final results: TTP frequency, TTPs per document, IoC frequency and type,
IoC/TTP co-occurrence across documents, etc.

All paths are computed from this file's own location
(Path(__file__).resolve()), so the script can be run from any computer
without editing hardcoded paths, as long as the project folder layout is
preserved.

Note: this repository does not include a script that converts
dataset_completo_limpio.json into the CSV consumed here. Generate it with
pandas (e.g. pandas.json_normalize on the JSON records) and place it at
extracts_ttps/output_dataset_limpio_v2.csv before running this script -
see dataset_analysis/README.md for details.
"""

import ast
import json
from pathlib import Path
from collections import Counter, defaultdict
import re

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sns.set_theme(style="whitegrid")

# =========================================================================
# CONFIGURATION - absolute paths derived from the project layout
# =========================================================================

DATASET_ANALYSIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DATASET_ANALYSIS_DIR.parent
EXTRACTS_DIR = PROJECT_ROOT / "extracts_ttps"

# Input CSV, generated from extracts_ttps/dataset_completo_limpio.json
csv_path = EXTRACTS_DIR / "output_dataset_limpio_v2.csv"

# Output folders for plots and CSV summaries, kept inside this folder.
PLOTS_DIR = DATASET_ANALYSIS_DIR / "plots_iocs"
PLOTS_FILTERED_DIR = DATASET_ANALYSIS_DIR / "plots_new_iocs_filtered"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_FILTERED_DIR.mkdir(parents=True, exist_ok=True)

if not csv_path.exists():
    raise FileNotFoundError(f"File not found: {csv_path.resolve()}")

df_raw = pd.read_csv(csv_path)

print("Shape:", df_raw.shape)
df_raw.head()
print("\nOriginal DataFrame info:")
df_raw.info()

def parse_complex_data(value):
    if pd.isna(value):
        return value
    value_str = str(value).strip()
    if value_str == "":
        return value
    try:
        return json.loads(value_str)
    except (json.JSONDecodeError, ValueError):
        try:
            return ast.literal_eval(value_str)
        except (ValueError, SyntaxError):
            return value


df = df_raw.copy()
for col in df.columns:
    df[col] = df[col].apply(parse_complex_data)

possible_ttp_cols = [c for c in df.columns if "ttp" in c.lower()]
print("Candidate TTP columns:", possible_ttp_cols)

ttp_col = "ttps" if "ttps" in df.columns else possible_ttp_cols[0]
print("Selected TTP column:", ttp_col)

df[ttp_col] = df[ttp_col].fillna("[]")
df[["file_name", ttp_col]].head()

def normalize_ttps_cell(value):
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    if isinstance(value, str):
        raw = value.strip()
        if raw == "":
            return []
        sep = ";" if ";" in raw else ","
        parts = [p.strip() for p in raw.split(sep) if p.strip()]
        return [{"technique": p, "technique_name": p} for p in parts]
    return []


df_ttps = df[["file_name", ttp_col]].copy()
df_ttps["ttp_item"] = df_ttps[ttp_col].apply(normalize_ttps_cell)
df_ttps = df_ttps.explode("ttp_item", ignore_index=True)
df_ttps = df_ttps[df_ttps["ttp_item"].notna()].copy()

df_ttps["technique"] = df_ttps["ttp_item"].apply(lambda x: str(x.get("technique", "N/A")).strip())
df_ttps["technique_name"] = df_ttps["ttp_item"].apply(lambda x: str(x.get("technique_name", "Unnamed")).strip())
df_ttps["ttp_label"] = df_ttps["technique"] + " - " + df_ttps["technique_name"]

df_ttps[["file_name", "technique", "technique_name", "ttp_label"]].head()

freq_df = (
    df_ttps["ttp_label"]
    .value_counts(dropna=False)
    .rename_axis("ttp")
    .reset_index(name="frequency")
    .sort_values("frequency", ascending=False)
    .reset_index(drop=True)
)

print("Total unique TTPs:", len(freq_df))
freq_df.head(20)

output_full_png = PLOTS_DIR / "plot_ttps_dataset_completo.png"

fig_height = max(8, min(0.32 * len(freq_df) + 2, 60))
plt.figure(figsize=(16, fig_height))
ax = sns.barplot(data=freq_df, y="ttp", x="frequency", color="#2B6CB0")
ax.set_title("Frequency of all TTPs in the full dataset", fontsize=14)
ax.set_xlabel("Frequency")
ax.set_ylabel("TTP")
plt.tight_layout()
plt.savefig(output_full_png, dpi=200)
plt.show()
print("Saved:", output_full_png.resolve())

top_n = 30
freq_top = freq_df.head(top_n)

plt.figure(figsize=(14, 10))
ax = sns.barplot(data=freq_top, y="ttp", x="frequency", color="#2F855A")
ax.set_title(f"Top {top_n} most frequent TTPs", fontsize=13)
ax.set_xlabel("Frequency")
ax.set_ylabel("TTP")
plt.tight_layout()
plt.savefig(PLOTS_DIR / f"plot_ttps_dataset_top_{top_n}.png", dpi=200)
plt.show()

top_n = 30
freq_top30 = freq_df.head(top_n).copy()

freq_top30["ttp_name"] = freq_top30["ttp"].apply(
    lambda s: s if " - " not in s else f"{s.split(' - ', 1)[0]}\n{s.split(' - ', 1)[1]}"
)

plt.figure(figsize=(20, 8))
ax = sns.barplot(data=freq_top30, x="ttp_name", y="frequency", color="#2F855A")
ax.set_title(f"Top {top_n} most frequent TTPs", fontsize=13)
ax.set_xlabel("TTP")
ax.set_ylabel("Frequency")

for p in ax.patches:
    height = p.get_height()
    ax.annotate(f"{int(height)}", (p.get_x() + p.get_width() / 2, height),
                ha="center", va="bottom", fontsize=8, xytext=(0, 3), textcoords="offset points")

plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig(PLOTS_DIR / f"histograma_top_{top_n}_ttps_vertical.png", dpi=200)
plt.show()

freq_top30[["ttp", "frequency"]]

ttps_por_doc = (
    df_ttps.groupby("file_name", as_index=False)["ttp_item"]
    .count()
    .rename(columns={"ttp_item": "n_ttps"})
    .sort_values("n_ttps", ascending=False)
)

p90 = ttps_por_doc["n_ttps"].quantile(0.90)
ttps_por_doc_p90 = ttps_por_doc[ttps_por_doc["n_ttps"] <= p90].copy()

print(f"90th percentile of n_ttps: {p90:.2f}")
print(f"Documents within P90: {len(ttps_por_doc_p90)} of {len(ttps_por_doc)}")

max_ttps_p90 = int(ttps_por_doc_p90["n_ttps"].max())
bins = range(0, max_ttps_p90 + 2)

plt.figure(figsize=(12, 6))
ax = sns.histplot(
    data=ttps_por_doc_p90,
    x="n_ttps",
    bins=bins,
    kde=True,
    color="#2B6CB0",
    edgecolor="white",
)
ax.set_title("Distribution of the number of TTPs per document (up to P90)", fontsize=13)
ax.set_xlabel("Number of TTPs found in the document")
ax.set_ylabel("Number of documents")

legend_handles = [
    Patch(facecolor="#2B6CB0", edgecolor="white", label="Histogram (document count)"),
    Line2D([0], [0], color="#2B6CB0", linewidth=2, label="Blue line: KDE density"),
]
ax.legend(handles=legend_handles, loc="upper right")

plt.tight_layout()
plt.savefig(PLOTS_DIR / "histograma_ttps_por_documento_p90.png", dpi=200)
plt.show()

ttps_por_doc.head(20)

ioc_columns = [c for c in df.columns if c.startswith("metadata.iocs.")]
print("Detected IOC columns:", ioc_columns)


def count_ioc_items(value):
    if isinstance(value, list):
        return len(value)
    if pd.isna(value):
        return 0
    return 1


df_iocs = df[["file_name"] + ioc_columns].copy()
for col in ioc_columns:
    df_iocs[col] = df_iocs[col].apply(count_ioc_items)

df_iocs["n_iocs"] = df_iocs[ioc_columns].sum(axis=1)
iocs_por_doc = df_iocs[["file_name", "n_iocs"]].sort_values("n_iocs", ascending=False)

print("\nQuick summary of IOCs per document:")
print(iocs_por_doc["n_iocs"].describe())

p90_iocs = iocs_por_doc["n_iocs"].quantile(0.90)
iocs_por_doc_p90 = iocs_por_doc[iocs_por_doc["n_iocs"] <= p90_iocs].copy()

print(f"\n90th percentile of n_iocs: {p90_iocs:.2f}")
print(f"Documents within P90: {len(iocs_por_doc_p90)} of {len(iocs_por_doc)}")

max_iocs_p90 = int(iocs_por_doc_p90["n_iocs"].max())
bins = range(0, max_iocs_p90 + 2)

plt.figure(figsize=(12, 6))
ax = sns.histplot(
    data=iocs_por_doc_p90,
    x="n_iocs",
    bins=bins,
    kde=True,
    color="#1E40AF",
    edgecolor="white",
)
ax.set_title("Distribution of the number of IOCs per document (up to P90)", fontsize=13)
ax.set_xlabel("Number of IOCs found in the document")
ax.set_ylabel("Number of documents")

legend_handles = [
    Patch(facecolor="#1E40AF", edgecolor="white", label="Histogram (document count)"),
    Line2D([0], [0], color="#1E40AF", linewidth=2, label="Blue line: KDE density"),
]
ax.legend(handles=legend_handles, loc="upper right")

plt.tight_layout()
plt.savefig(PLOTS_DIR / "histograma_iocs_por_documento_p90.png", dpi=200)
plt.show()

iocs_por_doc.head(20)

ioc_columns = [c for c in df.columns if c.startswith("metadata.iocs.")]
if not ioc_columns:
    raise ValueError("No metadata.iocs.* columns were found in the dataset")


def count_ioc_items(value):
    if isinstance(value, list):
        return len(value)
    if pd.isna(value):
        return 0
    return 1

df_ioc_doc = df[["file_name"] + ioc_columns].copy()
rename_map = {c: c.replace("metadata.iocs.", "") for c in ioc_columns}

for col in ioc_columns:
    df_ioc_doc[col] = df_ioc_doc[col].apply(count_ioc_items)

df_ioc_doc = df_ioc_doc.rename(columns=rename_map)
ioc_types = list(rename_map.values())

df_ioc_doc["total_iocs"] = df_ioc_doc[ioc_types].sum(axis=1)
df_ioc_doc = df_ioc_doc.sort_values("total_iocs", ascending=False).reset_index(drop=True)

max_docs_table = 40
df_plot = df_ioc_doc.head(max_docs_table).copy()

print(f"Documents shown: {len(df_plot)} (of {len(df_ioc_doc)} total)")
print(f"Average IOCs per document (global): {df_ioc_doc['total_iocs'].mean():.2f}")

heatmap_df = df_plot.set_index("file_name")[ioc_types]

plt.figure(figsize=(12, max(8, 0.35 * len(heatmap_df))))
ax = sns.heatmap(
    heatmap_df,
    cmap="YlGnBu",
    annot=True,
    fmt="d",
    linewidths=0.3,
    linecolor="white",
    cbar_kws={"label": "Number of IOCs"},
)
ax.set_title("Visual table (heatmap) of IOCs per document and type", fontsize=13)
ax.set_xlabel("IOC type")
ax.set_ylabel("Document")

plt.tight_layout()
plt.savefig(PLOTS_DIR / "tabla_heatmap_iocs_por_documento.png", dpi=200)
plt.show()

cols_show = ["file_name"] + ioc_types + ["total_iocs"]
df_plot[cols_show].head(20)

ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def extract_ips(value):
    ips = []
    if isinstance(value, list):
        for item in value:
            ips.extend(extract_ips(item))
        return ips
    if isinstance(value, dict):
        for v in value.values():
            ips.extend(extract_ips(v))
        return ips
    if isinstance(value, str):
        return ip_pattern.findall(value)
    return ips


if "metadata.iocs.ip" in df.columns:
    source_series = df["metadata.iocs.ip"]
else:
    ioc_columns = [c for c in df.columns if c.startswith("metadata.iocs.")]
    if not ioc_columns:
        raise ValueError("No metadata.iocs.* columns were found to extract IPs")
    source_series = df[ioc_columns].apply(lambda row: row.tolist(), axis=1)

all_ips = []
for value in source_series:
    if value is None:
        continue
    if isinstance(value, float) and pd.isna(value):
        continue
    if isinstance(value, str) and not value.strip():
        continue
    all_ips.extend(extract_ips(value))

ip_counts = Counter(all_ips)

if not ip_counts:
    raise ValueError("No IPs were detected in the dataset")

# IPs to exclude (common placeholder/example values)
EXCLUDE_IPS = {"1.0.0.0", "2.0.0.0", "1.2.3.4", "1.3.6.1"}

ip_freq_df = pd.DataFrame(ip_counts.items(), columns=["ip", "frequency"])
ip_freq_df = ip_freq_df[~ip_freq_df["ip"].isin(EXCLUDE_IPS)]  # <-- filter here
ip_freq_df = ip_freq_df.sort_values("frequency", ascending=False).head(20)

plt.figure(figsize=(12, 6))
ax = sns.barplot(
    data=ip_freq_df,
    x="ip",
    y="frequency",
    color="#2F855A",
    edgecolor="white",
)
ax.set_title(f"Top 20 most frequent IPs", fontsize=13)
ax.set_xlabel("IP address")
ax.set_ylabel("Number of occurrences")
plt.xticks(rotation=45, ha="right")

for p in ax.patches:
    height = p.get_height()
    ax.annotate(
        f"{int(height)}",
        (p.get_x() + p.get_width() / 2, height),
        ha="center",
        va="bottom",
        fontsize=9,
        xytext=(0, 3),
        textcoords="offset points",
    )

plt.tight_layout()
plt.savefig(PLOTS_DIR / "histograma_ips_mas_utilizadas.png", dpi=200)
plt.show()

ip_freq_df


def flatten_ioc_values(value):
    values = []
    if value is None:
        return values
    if isinstance(value, float) and pd.isna(value):
        return values
    if isinstance(value, list):
        for item in value:
            values.extend(flatten_ioc_values(item))
        return values
    if isinstance(value, dict):
        preferred_keys = ["value", "ioc", "indicator", "observable", "domain", "url", "hash"]
        for key in preferred_keys:
            if key in value:
                values.extend(flatten_ioc_values(value[key]))
                return values
        for v in value.values():
            values.extend(flatten_ioc_values(v))
        return values
    if isinstance(value, str):
        text = value.strip()
        if text:
            values.append(text)
        return values
    return values


ioc_columns_all = [c for c in df.columns if c.startswith("metadata.iocs.")]
resto_ioc_columns = [c for c in ioc_columns_all if c != "metadata.iocs.ip"]

if not resto_ioc_columns:
    raise ValueError("No additional IOC types were found besides IP")

selected_ioc_columns = resto_ioc_columns[:4]
print("IOC types selected for histograms:", selected_ioc_columns)

for col in selected_ioc_columns:
    ioc_type_name = col.replace("metadata.iocs.", "")

    all_values = []
    for cell_value in df[col]:
        all_values.extend(flatten_ioc_values(cell_value))

    counts = Counter(all_values)
    if not counts:
        print(f"No data for {ioc_type_name}; skipping plot.")
        continue

    top_n = 20
    freq_df_ioc = pd.DataFrame(counts.items(), columns=["ioc_value", "frequency"])
    freq_df_ioc = freq_df_ioc.sort_values("frequency", ascending=False).head(top_n)

    plt.figure(figsize=(12, 6))
    ax = sns.barplot(
        data=freq_df_ioc,
        x="ioc_value",
        y="frequency",
        color="#0F766E",
        edgecolor="white",
    )
    ax.set_title(f"Top {top_n} most frequent values ({ioc_type_name})", fontsize=13)
    ax.set_xlabel(f"IOC value ({ioc_type_name})")
    ax.set_ylabel("Number of occurrences")
    plt.xticks(rotation=45, ha="right")

    for p in ax.patches:
        height = p.get_height()
        ax.annotate(
            f"{int(height)}",
            (p.get_x() + p.get_width() / 2, height),
            ha="center",
            va="bottom",
            fontsize=9,
            xytext=(0, 3),
            textcoords="offset points",
        )

    plt.tight_layout()

    safe_type_name = re.sub(r"[^a-zA-Z0-9_-]", "_", ioc_type_name)
    output_path = PLOTS_DIR / f"histograma_{safe_type_name}_mas_utilizados.png"
    plt.savefig(output_path, dpi=200)
    plt.show()

    print("Saved:", output_path)

if len(resto_ioc_columns) < 4:
    print(f"Note: only {len(resto_ioc_columns)} additional IOC type(s) besides IP were found in the dataset.")

ioc_columns = [c for c in df.columns if c.startswith("metadata.iocs.")]
if not ioc_columns:
    raise ValueError("No metadata.iocs.* columns were found in the dataset")

ioc_to_docs = defaultdict(set)

for _, row in df[["file_name"] + ioc_columns].iterrows():
    doc_name = row["file_name"]
    iocs_in_doc = set()

    for col in ioc_columns:
        raw_values = flatten_ioc_values(row[col])

        for raw in raw_values:
            if col.endswith(".ip") or col.endswith(".ips"):
                ips_found = ip_pattern.findall(raw)
                if ips_found:
                    iocs_in_doc.update(ips_found)
                else:
                    iocs_in_doc.add(raw)
            else:
                iocs_in_doc.add(raw.lower())

    for ioc in iocs_in_doc:
        ioc_to_docs[ioc].add(doc_name)

coinc_df = pd.DataFrame(
    {
        "ioc": list(ioc_to_docs.keys()),
        "n_docs": [len(doc_set) for doc_set in ioc_to_docs.values()],
    }
).sort_values("n_docs", ascending=False)

coinc_df_multi = coinc_df[coinc_df["n_docs"] >= 2].copy()
if coinc_df_multi.empty:
    raise ValueError("There are no IOCs repeated across 2 or more documents")

p90_ioc_docs = coinc_df_multi["n_docs"].quantile(0.90)
coinc_df_top_p90 = coinc_df_multi[coinc_df_multi["n_docs"] >= p90_ioc_docs].copy()

print("Total distinct IOCs:", len(coinc_df))
print("IOCs in 2+ documents:", len(coinc_df_multi))
print(f"90th percentile of n_docs (over repeated IOCs): {p90_ioc_docs:.2f}")
print(f"IOCs in the high tier (>= P90): {len(coinc_df_top_p90)}")
print(f"n_docs range in the high tier: {coinc_df_top_p90['n_docs'].min()} to {coinc_df_top_p90['n_docs'].max()}")

min_docs = int(coinc_df_top_p90["n_docs"].min())
max_docs = int(coinc_df_top_p90["n_docs"].max())
bins = range(min_docs, max_docs + 2)

plt.figure(figsize=(12, 6))
ax = sns.histplot(
    data=coinc_df_top_p90,
    x="n_docs",
    bins=bins,
    kde=True,
    color="#0F766E",
    edgecolor="white",
)
ax.set_title("IOCs that co-occur the most across documents (P90 and above)", fontsize=13)
ax.set_xlabel("Number of documents in which an IOC appears")
ax.set_ylabel("Number of IOCs")

legend_handles = [
    Patch(facecolor="#0F766E", edgecolor="white", label="Histogram (IOC count)"),
    Line2D([0], [0], color="#0F766E", linewidth=2, label="Green line: KDE density"),
]
ax.legend(handles=legend_handles, loc="upper right")

plt.tight_layout()
plt.savefig(PLOTS_DIR / "histograma_iocs_coincidencia_top_p90.png", dpi=200)
plt.show()

# Bar chart: show the IOC value/name and how many documents it appears in
top_n = 20
ioc_top_values = coinc_df_multi.head(top_n).copy()


def shorten_label(text, max_len=85):
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


ioc_top_values["ioc_label"] = ioc_top_values["ioc"].apply(shorten_label)
ioc_top_values = ioc_top_values.sort_values("n_docs", ascending=True)

fig_height = max(8, 0.45 * len(ioc_top_values))
plt.figure(figsize=(14, fig_height))
ax = sns.barplot(
    data=ioc_top_values,
    y="ioc_label",
    x="n_docs",
    color="#1E40AF",
    edgecolor="white",
)
ax.set_title(f"Top {top_n} IOCs with the highest cross-document co-occurrence", fontsize=13)
ax.set_xlabel("Number of documents")
ax.set_ylabel("IOC value")

for p in ax.patches:
    width = p.get_width()
    ax.annotate(
        f"{int(width)}",
        (width, p.get_y() + p.get_height() / 2),
        ha="left",
        va="center",
        fontsize=9,
        xytext=(5, 0),
        textcoords="offset points",
    )

plt.tight_layout()
plt.savefig(PLOTS_DIR / "top_iocs_coincidencia_valor.png", dpi=200)
plt.show()

# Table to look up the full, untruncated value
ioc_top_values[["ioc", "n_docs"]]

# ---------------------------------------------------------------
# CSV: all IOCs with their document count, sorted descending
# ---------------------------------------------------------------
ioc_columns_csv = [c for c in df.columns if c.startswith("metadata.iocs.")]
print("IOC columns for the CSV:", ioc_columns_csv)

if not ioc_columns_csv:
    print("WARNING: no metadata.iocs.* columns were found; skipping the IOC CSV.")
else:
    all_ioc_to_docs = defaultdict(lambda: {"n_docs": set(), "type": ""})

    for _, row in df[["file_name"] + ioc_columns_csv].iterrows():
        doc_name = row["file_name"]

        for col in ioc_columns_csv:
            ioc_type = col.replace("metadata.iocs.", "")
            raw_values = flatten_ioc_values(row[col])

            for raw in raw_values:
                if col.endswith(".ip") or col.endswith(".ips"):
                    ips_found = ip_pattern.findall(raw)
                    candidates = ips_found if ips_found else [raw]
                else:
                    candidates = [raw.strip().lower()]

                for candidate in candidates:
                    if candidate:
                        all_ioc_to_docs[candidate]["n_docs"].add(doc_name)
                        all_ioc_to_docs[candidate]["type"] = ioc_type

    all_iocs_freq_df = (
        pd.DataFrame(
            {
                "ioc":    list(all_ioc_to_docs.keys()),
                "type":   [v["type"]  for v in all_ioc_to_docs.values()],
                "n_docs": [len(v["n_docs"]) for v in all_ioc_to_docs.values()],
            }
        )
        .sort_values("n_docs", ascending=False)
        .reset_index(drop=True)
    )

    print(f"Total distinct IOCs found: {len(all_iocs_freq_df)}")
    print(all_iocs_freq_df.head(10))

    output_csv_all_iocs = PLOTS_FILTERED_DIR / "todas_iocs_por_documentos.csv"
    all_iocs_freq_df.to_csv(output_csv_all_iocs, index=False, encoding="utf-8-sig")
    print(f"CSV saved at: {output_csv_all_iocs.resolve()}")

# ---------------------------------------------------------------
# TTPs that co-occur the most across documents (high tier: from P90)
# ---------------------------------------------------------------
ttp_docs_df = (
    df_ttps.groupby("ttp_label")["file_name"]
    .nunique()
    .reset_index(name="n_docs")
    .sort_values("n_docs", ascending=False)
)

ttp_docs_multi = ttp_docs_df[ttp_docs_df["n_docs"] >= 2].copy()
if ttp_docs_multi.empty:
    raise ValueError("There are no TTPs repeated across 2 or more documents")

p90_ttp_docs = ttp_docs_multi["n_docs"].quantile(0.90)
ttp_docs_top_p90 = ttp_docs_multi[ttp_docs_multi["n_docs"] >= p90_ttp_docs].copy()

print("Total distinct TTPs:", len(ttp_docs_df))
print("TTPs in 2+ documents:", len(ttp_docs_multi))
print(f"90th percentile of n_docs (over repeated TTPs): {p90_ttp_docs:.2f}")
print(f"TTPs in the high tier (>= P90): {len(ttp_docs_top_p90)}")
print(f"n_docs range in the high tier: {ttp_docs_top_p90['n_docs'].min()} to {ttp_docs_top_p90['n_docs'].max()}")

min_docs_ttp = int(ttp_docs_top_p90["n_docs"].min())
max_docs_ttp = int(ttp_docs_top_p90["n_docs"].max())
bins_ttp = range(min_docs_ttp, max_docs_ttp + 2)

plt.figure(figsize=(12, 6))
ax = sns.histplot(
    data=ttp_docs_top_p90,
    x="n_docs",
    bins=bins_ttp,
    kde=True,
    color="#7C3AED",
    edgecolor="white",
)
ax.set_title("TTPs that co-occur the most across documents (P90 and above)", fontsize=13)
ax.set_xlabel("Number of documents in which a TTP appears")
ax.set_ylabel("Number of TTPs")

legend_handles = [
    Patch(facecolor="#7C3AED", edgecolor="white", label="Histogram (TTP count)"),
    Line2D([0], [0], color="#7C3AED", linewidth=2, label="Purple line: KDE density"),
]
ax.legend(handles=legend_handles, loc="upper right")

plt.tight_layout()
plt.savefig(PLOTS_DIR / "histograma_ttps_coincidencia_top_p90.png", dpi=200)
plt.show()

max_top_ttps = 20
ttp_top_values = ttp_docs_multi.head(max_top_ttps).copy()


def shorten_label(text, max_len=90):
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


ttp_top_values["ttp_label_short"] = ttp_top_values["ttp_label"].apply(shorten_label)
ttp_top_values = ttp_top_values.sort_values("n_docs", ascending=True)

fig_height = max(8, 0.45 * len(ttp_top_values))
plt.figure(figsize=(14, fig_height))
ax = sns.barplot(
    data=ttp_top_values,
    y="ttp_label_short",
    x="n_docs",
    color="#4338CA",
    edgecolor="white",
)
ax.set_title(f"Top {max_top_ttps} TTPs with the highest cross-document co-occurrence", fontsize=13)
ax.set_xlabel("Number of documents")
ax.set_ylabel("TTP")

for p in ax.patches:
    width = p.get_width()
    ax.annotate(
        f"{int(width)}",
        (width, p.get_y() + p.get_height() / 2),
        ha="left",
        va="center",
        fontsize=9,
        xytext=(5, 0),
        textcoords="offset points",
    )

plt.tight_layout()
plt.savefig(PLOTS_DIR / "top_ttps_coincidencia_valor.png", dpi=200)
plt.show()

ttp_top_values[["ttp_label", "n_docs"]]
