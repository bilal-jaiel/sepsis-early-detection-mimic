import os
from pathlib import Path

# Working directory for intermediate files (git-ignored), override with WAVEFORM_WORKDIR
WORK_DIR = Path(os.environ.get("WAVEFORM_WORKDIR", Path(__file__).resolve().parents[2] / "data" / "waveforms"))

import pandas as pd

INPUT_PATH = str(WORK_DIR / "output" / "wfdb_window_features_cleaned.csv")
OUTPUT_PATH = str(WORK_DIR / "output" / "wfdb_window_features_core_sepsis.csv")
REPORT_PATH = str(WORK_DIR / "output" / "wfdb_window_features_core_sepsis_report.txt")

# colonne da mantenere sempre
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

# flag di presenza canali
flag_cols = [c for c in ["has_ii", "has_v", "has_avr", "has_pleth", "has_resp"] if c in pd.read_csv(INPUT_PATH, nrows=0).columns]

# segnali core
core_signals = {"ii", "v", "avr", "pleth", "resp", "abp", "art", "cvp"}

# statistiche da tenere, includendo missing_ratio
core_stats = {
    "mean",
    "std",
    "p10",
    "p90",
    "iqr",
    "range",
    "diff_std",
    "missing_ratio",
}

print("Loading cleaned dataset...")
df = pd.read_csv(INPUT_PATH)
initial_shape = df.shape

selected_signal_cols = []

for col in df.columns:
    if not col.startswith("sig_") or "__" not in col:
        continue

    left, stat = col.split("__", 1)
    signal = left.replace("sig_", "")

    if signal in core_signals and stat in core_stats:
        selected_signal_cols.append(col)

keep_cols = [c for c in id_cols if c in df.columns]
keep_cols += flag_cols
keep_cols += selected_signal_cols

# rimuovi duplicati mantenendo ordine
keep_cols = list(dict.fromkeys(keep_cols))

all_cols = set(df.columns)
kept_set = set(keep_cols)
dropped_cols = sorted(all_cols - kept_set)

df_selected = df[keep_cols].copy()
final_shape = df_selected.shape

df_selected.to_csv(OUTPUT_PATH, index=False)

# riepilogo segnali
all_signal_cols = [c for c in df.columns if c.startswith("sig_") and "__" in c]
kept_signal_cols = [c for c in keep_cols if c.startswith("sig_") and "__" in c]

all_signals = sorted({c.split("__")[0].replace("sig_", "") for c in all_signal_cols})
kept_signals = sorted({c.split("__")[0].replace("sig_", "") for c in kept_signal_cols})
fully_removed_signals = sorted(set(all_signals) - set(kept_signals))

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write("CORE SEPSIS FEATURE SELECTION REPORT (WITH MISSING RATIO)\n")
    f.write("=" * 70 + "\n\n")

    f.write("SHAPES\n")
    f.write(f"Initial shape: {initial_shape}\n")
    f.write(f"Final shape: {final_shape}\n\n")

    f.write(f"Total columns kept: {len(keep_cols)}\n")
    f.write(f"Total columns dropped: {len(dropped_cols)}\n\n")

    f.write("KEPT IDENTIFIER COLUMNS:\n")
    for c in id_cols:
        if c in keep_cols:
            f.write(f"  - {c}\n")
    f.write("\n")

    f.write("KEPT FLAG COLUMNS:\n")
    for c in flag_cols:
        if c in keep_cols:
            f.write(f"  - {c}\n")
    f.write("\n")

    f.write("KEPT SIGNAL FEATURES:\n")
    for c in sorted(selected_signal_cols):
        f.write(f"  - {c}\n")
    f.write("\n")

    f.write("DROPPED COLUMNS (FULL LIST):\n")
    for c in dropped_cols:
        f.write(f"  - {c}\n")
    f.write("\n")

    f.write("SIGNALS PRESENT IN FINAL DATASET:\n")
    for s in kept_signals:
        f.write(f"  - {s}\n")
    f.write("\n")

    f.write("COMPLETELY REMOVED SIGNALS:\n")
    if fully_removed_signals:
        for s in fully_removed_signals:
            f.write(f"  - {s}\n")
    else:
        f.write("  - None\n")

print(f"Initial shape: {initial_shape}")
print(f"Selected signal feature columns: {len(selected_signal_cols)}")
print(f"Final shape: {final_shape}")
print(f"Saved dataset to: {OUTPUT_PATH}")
print(f"Saved full report to: {REPORT_PATH}")