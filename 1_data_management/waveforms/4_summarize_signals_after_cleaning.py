import os
from pathlib import Path

# Working directory for intermediate files (git-ignored), override with WAVEFORM_WORKDIR
WORK_DIR = Path(os.environ.get("WAVEFORM_WORKDIR", Path(__file__).resolve().parents[2] / "data" / "waveforms"))

from pathlib import Path
import pandas as pd
from collections import defaultdict

# =========================
# PATH
# =========================
INPUT_PATH = str(WORK_DIR / "output" / "02_wfdb_window_features_cleaned.csv")
OUTPUT_DIR = (WORK_DIR / "output" / "02b_signal_summary")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOAD
# =========================
print("Loading cleaned dataset...")
df = pd.read_csv(INPUT_PATH)

print(f"Shape: {df.shape}")

# =========================
# PARSE SIGNAL FEATURES
# =========================
signal_to_features = defaultdict(list)

for col in df.columns:
    if col.startswith("sig_") and "__" in col:
        left, right = col.split("__", 1)
        signal_name = left.replace("sig_", "")
        feature_name = right
        signal_to_features[signal_name].append(feature_name)

# =========================
# BUILD SUMMARY TABLE
# =========================
rows = []

for signal_name, feats in signal_to_features.items():
    unique_feats = sorted(set(feats))
    rows.append({
        "signal": signal_name,
        "n_features": len(unique_feats),
        "features": ", ".join(unique_feats)
    })

summary_df = pd.DataFrame(rows).sort_values("n_features", ascending=False)

# =========================
# PRINT
# =========================
print("\n" + "=" * 80)
print("SIGNAL SUMMARY")
print("=" * 80)
print(summary_df)

# =========================
# SAVE SUMMARY
# =========================
summary_df.to_csv(OUTPUT_DIR / "signals_summary.csv", index=False)

# salva anche un file per segnale
for signal_name, feats in signal_to_features.items():
    unique_feats = sorted(set(feats))
    pd.DataFrame({"feature": unique_feats}).to_csv(
        OUTPUT_DIR / f"{signal_name}_features.csv", index=False
    )

print("\nSaved to:")
print(OUTPUT_DIR)