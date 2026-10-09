import os
from pathlib import Path

# Working directory for intermediate files (git-ignored), override with WAVEFORM_WORKDIR
WORK_DIR = Path(os.environ.get("WAVEFORM_WORKDIR", Path(__file__).resolve().parents[2] / "data" / "waveforms"))

import pandas as pd
from pathlib import Path
from tqdm import tqdm

# ===== PATH =====
BASE_DIR = WORK_DIR
INPUT_CSV = BASE_DIR / "output" / "03b_wfdb_augmented_standard_names.csv"
OUTPUT_CSV = BASE_DIR / "output" / "usagi_input.csv"

print("Loading dataset...")

df = pd.read_csv(INPUT_CSV)
print(f"Dataset shape: {df.shape}")

print("Building Usagi table...")

rows = []

# Filtra solo feature utili (evita ID)
feature_cols = [
    col for col in df.columns
    if not col.endswith("_id")
    and "datetime" not in col
    and "index" not in col
]

for col in tqdm(feature_cols, desc="Processing features"):
    freq = df[col].notna().sum()

    rows.append({
        "code": col,
        "description": col,
        "frequency": int(freq)
    })

usagi_df = pd.DataFrame(rows)

print("Saving Usagi input...")

usagi_df.to_csv(OUTPUT_CSV, index=False)

print("Done.")
print(f"Saved to: {OUTPUT_CSV}")