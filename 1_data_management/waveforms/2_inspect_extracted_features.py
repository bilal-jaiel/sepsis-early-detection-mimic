from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect extracted WFDB feature table.")
    parser.add_argument(
        "--input-csv",
        type=str,
        required=True,
        help="Path to extracted feature CSV"
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="output/01b_inspection",
        help="Directory where summary CSV files will be saved"
    )
    args = parser.parse_args()

    input_csv = Path(args.input_csv).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_csv.exists():
        raise FileNotFoundError(f"CSV not found: {input_csv}")

    df = pd.read_csv(input_csv)

    print_section("DATASET SHAPE")
    print(f"Rows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")

    print_section("FIRST 5 ROWS")
    print(df.head())

    print_section("COLUMN NAMES")
    for c in df.columns:
        print(c)

    print_section("MISSING VALUES (%)")
    missing_pct = (df.isna().mean() * 100).sort_values(ascending=False)
    print(missing_pct.head(50))

    missing_pct.to_csv(out_dir / "missing_percent.csv", header=["missing_percent"])

    print_section("NUMERIC SUMMARY")
    numeric_df = df.select_dtypes(include=["number"])
    if not numeric_df.empty:
        summary = numeric_df.describe().T
        print(summary.head(50))
        summary.to_csv(out_dir / "numeric_summary.csv")
    else:
        print("No numeric columns found.")

    has_cols = [c for c in df.columns if c.startswith("has_")]
    if has_cols:
        print_section("CHANNEL PRESENCE COUNTS")
        presence = pd.DataFrame({
            "column": has_cols,
            "sum": [df[c].fillna(0).sum() for c in has_cols],
            "mean": [df[c].fillna(0).mean() for c in has_cols],
        }).sort_values("sum", ascending=False)
        print(presence)
        presence.to_csv(out_dir / "channel_presence.csv", index=False)

    id_cols = [c for c in ["patient_id", "study_id", "record_id", "segment_id"] if c in df.columns]
    if id_cols:
        print_section("UNIQUE COUNTS")
        for c in id_cols:
            print(f"{c}: {df[c].nunique()}")

    if "window_duration_sec" in df.columns:
        print_section("WINDOW DURATION COUNTS")
        print(df["window_duration_sec"].value_counts(dropna=False).head(20))

    if "segment_duration_sec" in df.columns:
        print_section("SEGMENT DURATION SUMMARY")
        print(df["segment_duration_sec"].describe())

    if "patient_id" in df.columns:
        print_section("ROWS PER PATIENT")
        rows_per_patient = df.groupby("patient_id").size().sort_values(ascending=False)
        print(rows_per_patient.head(20))
        rows_per_patient.to_csv(out_dir / "rows_per_patient.csv", header=["n_rows"])

    if "record_id" in df.columns:
        print_section("ROWS PER RECORD")
        rows_per_record = df.groupby("record_id").size().sort_values(ascending=False)
        print(rows_per_record.head(20))
        rows_per_record.to_csv(out_dir / "rows_per_record.csv", header=["n_rows"])

    print_section("USEFUL FEATURE COLUMNS PREVIEW")
    feature_cols = [
        c for c in df.columns
        if c.startswith("sig_") or c.startswith("num_")
    ]
    for c in feature_cols[:100]:
        print(c)

    pd.DataFrame({"feature_columns": feature_cols}).to_csv(
        out_dir / "feature_columns.csv", index=False
    )

    print_section("DONE")
    print(f"Saved summaries to: {out_dir}")


if __name__ == "__main__":
    main()