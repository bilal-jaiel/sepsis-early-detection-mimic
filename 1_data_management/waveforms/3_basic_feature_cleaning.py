import os
from pathlib import Path

# Working directory for intermediate files (git-ignored), override with WAVEFORM_WORKDIR
WORK_DIR = Path(os.environ.get("WAVEFORM_WORKDIR", Path(__file__).resolve().parents[2] / "data" / "waveforms"))

import pandas as pd
import numpy as np

# =========================
# PATH
# =========================
INPUT_PATH = str(WORK_DIR / "output" / "wfdb_window_features.csv")
OUTPUT_PATH = str(WORK_DIR / "output" / "02_wfdb_window_features_cleaned.csv")
REPORT_PATH = str(WORK_DIR / "output" / "02_wfdb_window_features_cleaning_report.txt")

# =========================
# SETTINGS
# =========================
MISSING_THRESHOLD = 0.95
CONSTANT_THRESHOLD = 0.995

# =========================
# LOAD
# =========================
print("Loading dataset...")
df = pd.read_csv(INPUT_PATH)
print(f"Initial shape: {df.shape}")

# =========================
# COLUMN GROUPS
# =========================
id_cols = [
    "patient_id",
    "study_id",
    "record_id",
    "segment_id",
    "segment_index",
    "relative_segment_path",
    "fs",
    "segment_duration_sec",
    "window_index",
    "window_start_sec",
    "window_end_sec",
    "window_duration_sec",
    "window_valid_fraction",
    "n_signals",
]

flag_cols = [col for col in df.columns if col.startswith("has_")]
unit_cols = [col for col in df.columns if col.endswith("__unit")]

protected_cols = set(id_cols + flag_cols)

all_feature_cols = [
    col for col in df.columns
    if col not in protected_cols and col not in unit_cols
]

print(f"Protected columns: {len(protected_cols)}")
print(f"Unit columns to remove: {len(unit_cols)}")
print(f"Candidate feature columns: {len(all_feature_cols)}")

# =========================
# 1. DROP UNIT COLUMNS
# =========================
df = df.drop(columns=unit_cols, errors="ignore")

# =========================
# 2. DROP HIGH-MISSING FEATURES
# =========================
missing_ratio = df[all_feature_cols].isna().mean()
high_missing_cols = missing_ratio[missing_ratio > MISSING_THRESHOLD].index.tolist()

df = df.drop(columns=high_missing_cols, errors="ignore")

remaining_feature_cols = [
    col for col in all_feature_cols if col not in high_missing_cols
]

print(f"Dropped high-missing feature columns: {len(high_missing_cols)}")

# =========================
# 3. DROP NEAR-CONSTANT FEATURES
# =========================
low_variance_cols = []

for col in remaining_feature_cols:
    series = df[col]

    non_na = series.dropna()
    if len(non_na) == 0:
        low_variance_cols.append(col)
        continue

    top_freq = non_na.value_counts(normalize=True).iloc[0]

    if top_freq > CONSTANT_THRESHOLD:
        low_variance_cols.append(col)

df = df.drop(columns=low_variance_cols, errors="ignore")

final_feature_cols = [
    col for col in remaining_feature_cols if col not in low_variance_cols
]

print(f"Dropped near-constant feature columns: {len(low_variance_cols)}")

# =========================
# SAVE CLEAN DATASET
# =========================
print(f"Final shape: {df.shape}")
df.to_csv(OUTPUT_PATH, index=False)
print(f"Saved cleaned dataset to: {OUTPUT_PATH}")

# =========================
# SAVE REPORT
# =========================
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write("WFDB FEATURE CLEANING REPORT\n")
    f.write("=" * 50 + "\n\n")
    f.write(f"Initial shape: {df.shape}\n")
    f.write(f"Missing threshold: {MISSING_THRESHOLD}\n")
    f.write(f"Constant threshold: {CONSTANT_THRESHOLD}\n\n")

    f.write(f"Removed unit columns ({len(unit_cols)}):\n")
    for c in unit_cols:
        f.write(f"  - {c}\n")
    f.write("\n")

    f.write(f"Removed high-missing columns ({len(high_missing_cols)}):\n")
    for c in high_missing_cols:
        f.write(f"  - {c}\n")
    f.write("\n")

    f.write(f"Removed near-constant columns ({len(low_variance_cols)}):\n")
    for c in low_variance_cols:
        f.write(f"  - {c}\n")
    f.write("\n")

    f.write(f"Remaining feature columns ({len(final_feature_cols)}):\n")
    for c in final_feature_cols:
        f.write(f"  - {c}\n")

print(f"Saved cleaning report to: {REPORT_PATH}")