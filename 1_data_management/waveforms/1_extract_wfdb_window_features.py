from __future__ import annotations

import argparse
import gzip
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import wfdb


# =========================
# Logging
# =========================

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )


# =========================
# Helpers
# =========================

SEGMENT_PATTERN = re.compile(r"^(?P<record_id>\d+)_(?P<segment_idx>\d+)$")


def safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    except Exception:
        return None


def sanitize_name(name: str) -> str:
    s = "".join(ch if ch.isalnum() else "_" for ch in name.strip())
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_").lower()


def infer_patient_and_study(path: Path, root: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Tries to infer:
      - patient_id: folder like p100
      - study_id: folder like p10039708
    anywhere in the relative path below root.
    """
    rel_parts = path.relative_to(root).parts
    patient_id = None
    study_id = None

    for part in rel_parts:
        if re.fullmatch(r"p\d{3}", part):
            patient_id = part
        elif re.fullmatch(r"p\d{8}", part):
            study_id = part

    return patient_id, study_id


def find_segment_stems(root: Path) -> List[Path]:
    """
    Find all segment .hea files of the form XXXXXXXX_YYYY.hea
    and return stems without extension.
    """
    stems: List[Path] = []
    for hea in root.rglob("*.hea"):
        if SEGMENT_PATTERN.fullmatch(hea.stem):
            stems.append(hea.with_suffix(""))
    return sorted(stems)


def find_numerics_file_for_record(segment_stem: Path) -> Optional[Path]:
    """
    For a segment like .../81739927/81739927_0005.hea
    try to find .../81739927/81739927n.csv.gz
    """
    match = SEGMENT_PATTERN.fullmatch(segment_stem.name)
    if not match:
        return None

    record_id = match.group("record_id")
    candidate = segment_stem.parent / f"{record_id}n.csv.gz"
    return candidate if candidate.exists() else None


# =========================
# Feature extraction
# =========================

def compute_basic_features(x: np.ndarray, prefix: str) -> Dict[str, Optional[float]]:
    """
    Generic numeric features for one signal inside one time window.
    """
    out: Dict[str, Optional[float]] = {}

    if x is None or len(x) == 0:
        keys = [
            "mean", "std", "min", "max", "median",
            "p10", "p25", "p75", "p90",
            "rms", "iqr", "range", "abs_mean",
            "diff_mean", "diff_std", "zero_crossings",
            "missing_ratio"
        ]
        return {f"{prefix}__{k}": None for k in keys}

    arr = np.asarray(x, dtype=np.float64)
    missing_ratio = float(np.isnan(arr).mean())

    valid = arr[~np.isnan(arr)]
    if valid.size == 0:
        keys = [
            "mean", "std", "min", "max", "median",
            "p10", "p25", "p75", "p90",
            "rms", "iqr", "range", "abs_mean",
            "diff_mean", "diff_std", "zero_crossings"
        ]
        out = {f"{prefix}__{k}": None for k in keys}
        out[f"{prefix}__missing_ratio"] = missing_ratio
        return out

    diffs = np.diff(valid) if valid.size > 1 else np.array([], dtype=np.float64)

    # zero crossings relative to mean-centered signal
    centered = valid - np.mean(valid)
    zc = np.sum(centered[:-1] * centered[1:] < 0) if valid.size > 1 else 0

    out[f"{prefix}__mean"] = safe_float(np.mean(valid))
    out[f"{prefix}__std"] = safe_float(np.std(valid))
    out[f"{prefix}__min"] = safe_float(np.min(valid))
    out[f"{prefix}__max"] = safe_float(np.max(valid))
    out[f"{prefix}__median"] = safe_float(np.median(valid))
    out[f"{prefix}__p10"] = safe_float(np.percentile(valid, 10))
    out[f"{prefix}__p25"] = safe_float(np.percentile(valid, 25))
    out[f"{prefix}__p75"] = safe_float(np.percentile(valid, 75))
    out[f"{prefix}__p90"] = safe_float(np.percentile(valid, 90))
    out[f"{prefix}__rms"] = safe_float(np.sqrt(np.mean(valid ** 2)))
    out[f"{prefix}__iqr"] = safe_float(np.percentile(valid, 75) - np.percentile(valid, 25))
    out[f"{prefix}__range"] = safe_float(np.max(valid) - np.min(valid))
    out[f"{prefix}__abs_mean"] = safe_float(np.mean(np.abs(valid)))
    out[f"{prefix}__diff_mean"] = safe_float(np.mean(diffs)) if diffs.size else None
    out[f"{prefix}__diff_std"] = safe_float(np.std(diffs)) if diffs.size else None
    out[f"{prefix}__zero_crossings"] = safe_float(zc)
    out[f"{prefix}__missing_ratio"] = safe_float(missing_ratio)

    return out


def summarize_numerics_in_window(
    numerics_df: pd.DataFrame,
    start_sec: float,
    end_sec: float,
    time_col: str = "time"
) -> Dict[str, Optional[float]]:
    """
    Summarize numerics rows falling inside the waveform window.
    This is best-effort because numerics schemas can vary.
    """
    if numerics_df.empty or time_col not in numerics_df.columns:
        return {}

    sub = numerics_df[(numerics_df[time_col] >= start_sec) & (numerics_df[time_col] < end_sec)]
    if sub.empty:
        return {}

    out: Dict[str, Optional[float]] = {}
    numeric_cols = [
        c for c in sub.columns
        if c != time_col and pd.api.types.is_numeric_dtype(sub[c])
    ]

    for col in numeric_cols:
        vals = sub[col].dropna().to_numpy(dtype=np.float64)
        prefix = f"num_{sanitize_name(col)}"
        if vals.size == 0:
            out[f"{prefix}__mean"] = None
            out[f"{prefix}__min"] = None
            out[f"{prefix}__max"] = None
            out[f"{prefix}__count"] = 0
        else:
            out[f"{prefix}__mean"] = safe_float(np.mean(vals))
            out[f"{prefix}__min"] = safe_float(np.min(vals))
            out[f"{prefix}__max"] = safe_float(np.max(vals))
            out[f"{prefix}__count"] = int(vals.size)

    return out


# =========================
# Numerics loading
# =========================

def load_numerics_csv_best_effort(path: Path) -> pd.DataFrame:
    """
    Loads record_id n.csv.gz.
    Since schemas can vary, this is intentionally permissive.
    """
    try:
        df = pd.read_csv(path, compression="gzip")
    except Exception as e:
        logging.warning("Failed to read numerics file %s: %s", path, e)
        return pd.DataFrame()

    # Try to identify a time column
    candidate_time_cols = ["time", "Time", "seconds", "Seconds", "t", "charttime"]
    found = None
    for c in candidate_time_cols:
        if c in df.columns:
            found = c
            break

    if found is None:
        # If there is a first numeric-looking column, use it as time
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]):
                found = c
                break

    if found is not None and found != "time":
        df = df.rename(columns={found: "time"})

    return df


# =========================
# Core pipeline
# =========================

def process_segment(
    segment_stem: Path,
    root: Path,
    window_seconds: float,
    min_valid_fraction: float,
    use_numerics: bool
) -> List[Dict[str, Any]]:
    """
    Process one segment and return one row per time window.
    """
    rows: List[Dict[str, Any]] = []

    patient_id, study_id = infer_patient_and_study(segment_stem, root)

    match = SEGMENT_PATTERN.fullmatch(segment_stem.name)
    if not match:
        return rows

    record_id = match.group("record_id")
    segment_idx = int(match.group("segment_idx"))

    try:
        record = wfdb.rdrecord(str(segment_stem))
    except Exception as e:
        logging.warning("Failed to read %s: %s", segment_stem, e)
        return rows

    p_signal = getattr(record, "p_signal", None)
    if p_signal is None:
        return rows

    x = np.asarray(p_signal)
    if x.ndim != 2 or x.shape[0] == 0:
        return rows

    fs = safe_float(getattr(record, "fs", None))
    if fs is None or fs <= 0:
        return rows

    sig_names = list(getattr(record, "sig_name", None) or [f"sig_{i}" for i in range(x.shape[1])])
    units = list(getattr(record, "units", None) or [None] * x.shape[1])

    sig_len = int(getattr(record, "sig_len", x.shape[0]))
    duration_seconds = sig_len / fs

    samples_per_window = max(1, int(round(window_seconds * fs)))

    numerics_df = pd.DataFrame()
    numerics_path = find_numerics_file_for_record(segment_stem) if use_numerics else None
    if numerics_path is not None:
        numerics_df = load_numerics_csv_best_effort(numerics_path)

    n_windows = int(np.ceil(sig_len / samples_per_window))

    for w in range(n_windows):
        start_idx = w * samples_per_window
        end_idx = min((w + 1) * samples_per_window, sig_len)

        if end_idx <= start_idx:
            continue

        window_len = end_idx - start_idx
        valid_fraction = window_len / samples_per_window
        if valid_fraction < min_valid_fraction:
            continue

        start_sec = start_idx / fs
        end_sec = end_idx / fs

        row: Dict[str, Any] = {
            "patient_id": patient_id,
            "study_id": study_id,
            "record_id": record_id,
            "segment_id": f"{record_id}_{segment_idx:04d}",
            "segment_index": segment_idx,
            "relative_segment_path": str(segment_stem.relative_to(root)),
            "fs": fs,
            "segment_duration_sec": safe_float(duration_seconds),
            "window_index": w,
            "window_start_sec": safe_float(start_sec),
            "window_end_sec": safe_float(end_sec),
            "window_duration_sec": safe_float(end_sec - start_sec),
            "window_valid_fraction": safe_float(valid_fraction),
            "n_signals": len(sig_names),
            "has_ii": int("II" in sig_names),
            "has_v": int("V" in sig_names),
            "has_avr": int("aVR" in sig_names),
            "has_pleth": int("Pleth" in sig_names),
            "has_resp": int("Resp" in sig_names),
        }

        for ch_idx, raw_name in enumerate(sig_names):
            clean = sanitize_name(raw_name)
            prefix = f"sig_{clean}"

            window_signal = x[start_idx:end_idx, ch_idx]
            feats = compute_basic_features(window_signal, prefix)
            row.update(feats)

            unit = units[ch_idx] if ch_idx < len(units) else None
            row[f"{prefix}__unit"] = unit

        if use_numerics and not numerics_df.empty:
            row.update(summarize_numerics_in_window(numerics_df, start_sec, end_sec, time_col="time"))

        rows.append(row)

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract one-row-per-window features from MIMIC WFDB waveforms.")
    parser.add_argument(
        "--input-root",
        type=str,
        required=True,
        help="Path to waves root, e.g. path/to/physionet.org/files/mimic4wdb/0.1.0/waves"
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="output/01_wfdb_window_features.csv",
        help="Output CSV file"
    )
    parser.add_argument(
        "--window-seconds",
        type=float,
        default=30.0,
        help="Window length in seconds"
    )
    parser.add_argument(
        "--min-valid-fraction",
        type=float,
        default=0.8,
        help="Minimum fraction of a full window required to keep last partial windows"
    )
    parser.add_argument(
        "--max-segments",
        type=int,
        default=None,
        help="Optional debug limit"
    )
    parser.add_argument(
        "--use-numerics",
        action="store_true",
        help="If set, tries to load record-level n.csv.gz and summarize numerics per window"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    root = Path(args.input_root).resolve()
    output_csv = Path(args.output_csv).resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    if not root.exists():
        raise FileNotFoundError(f"Input root not found: {root}")

    segment_stems = find_segment_stems(root)
    logging.info("Found %d candidate segment headers", len(segment_stems))

    if args.max_segments is not None:
        segment_stems = segment_stems[:args.max_segments]
        logging.info("Using first %d segments due to --max-segments", len(segment_stems))

    all_rows: List[Dict[str, Any]] = []

    for i, stem in enumerate(segment_stems, start=1):
        logging.info("Processing %d/%d: %s", i, len(segment_stems), stem)
        rows = process_segment(
            segment_stem=stem,
            root=root,
            window_seconds=args.window_seconds,
            min_valid_fraction=args.min_valid_fraction,
            use_numerics=args.use_numerics
        )
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)

    if df.empty:
        logging.warning("No rows were generated.")
    else:
        df.to_csv(output_csv, index=False)
        logging.info("Saved CSV: %s (%d rows, %d cols)", output_csv, len(df), len(df.columns))

    logging.info("Done.")


if __name__ == "__main__":
    main()