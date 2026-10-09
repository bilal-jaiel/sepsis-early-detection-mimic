import os
from pathlib import Path

# Working directory for intermediate files (git-ignored), override with WAVEFORM_WORKDIR
WORK_DIR = Path(os.environ.get("WAVEFORM_WORKDIR", Path(__file__).resolve().parents[2] / "data" / "waveforms"))

import re
import argparse
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import wfdb
from scipy.signal import find_peaks
from tqdm import tqdm


SEGMENT_PATTERN = re.compile(r"^(?P<record_id>\d+)_(?P<segment_idx>\d+)$")


def safe_float(x):
    try:
        x = float(x)
        if np.isnan(x) or np.isinf(x):
            return np.nan
        return x
    except Exception:
        return np.nan


def sanitize_name(name):
    s = "".join(ch if ch.isalnum() else "_" for ch in name.strip())
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_").lower()


def infer_patient_and_study(path: Path, root: Path):
    rel_parts = path.relative_to(root).parts
    patient_id = None
    study_id = None

    for part in rel_parts:
        if re.fullmatch(r"p\d{3}", part):
            patient_id = part
        elif re.fullmatch(r"p\d{8}", part):
            study_id = part

    return patient_id, study_id


def find_segment_stems(root: Path):
    stems = []
    for hea in root.rglob("*.hea"):
        if SEGMENT_PATTERN.fullmatch(hea.stem):
            stems.append(hea.with_suffix(""))
    return sorted(stems)


def get_record_start_datetime(record):
    base_date = getattr(record, "base_date", None)
    base_time = getattr(record, "base_time", None)

    if base_date is None or base_time is None:
        return None

    try:
        return datetime.combine(base_date, base_time)
    except Exception:
        return None


def derive_ecg_features(ecg, fs):
    out = {
        "derived_ecg_hr_mean_bpm": np.nan,
        "derived_ecg_hr_std_bpm": np.nan,
        "derived_ecg_hrv_sdnn_ms": np.nan,
        "derived_ecg_hrv_rmssd_ms": np.nan,
        "derived_ecg_n_beats": np.nan,
    }

    ecg = np.asarray(ecg, dtype=float)
    ecg = ecg[~np.isnan(ecg)]

    if len(ecg) < fs * 5:
        return out

    ecg_centered = ecg - np.nanmedian(ecg)
    min_distance = int(0.27 * fs)
    prominence = np.nanstd(ecg_centered) * 0.5

    try:
        peaks, _ = find_peaks(
            ecg_centered,
            distance=max(1, min_distance),
            prominence=prominence,
        )
    except Exception:
        return out

    if len(peaks) < 3:
        return out

    rr = np.diff(peaks) / fs
    rr = rr[(rr > 60 / 220) & (rr < 60 / 30)]

    if len(rr) < 2:
        return out

    hr = 60 / rr

    out["derived_ecg_hr_mean_bpm"] = safe_float(np.mean(hr))
    out["derived_ecg_hr_std_bpm"] = safe_float(np.std(hr))
    out["derived_ecg_hrv_sdnn_ms"] = safe_float(np.std(rr) * 1000)
    out["derived_ecg_hrv_rmssd_ms"] = safe_float(
        np.sqrt(np.mean(np.diff(rr) ** 2)) * 1000
    )
    out["derived_ecg_n_beats"] = safe_float(len(peaks))

    return out


def derive_pressure_features(bp, fs, prefix):
    out = {
        f"{prefix}_systolic_mean": np.nan,
        f"{prefix}_diastolic_mean": np.nan,
        f"{prefix}_map_mean": np.nan,
        f"{prefix}_pulse_pressure_mean": np.nan,
        f"{prefix}_n_pulses": np.nan,
    }

    bp = np.asarray(bp, dtype=float)
    bp = bp[~np.isnan(bp)]

    if len(bp) < fs * 5:
        return out

    min_distance = int(0.3 * fs)
    prominence = np.nanstd(bp) * 0.3

    try:
        peaks, _ = find_peaks(bp, distance=max(1, min_distance), prominence=prominence)
        troughs, _ = find_peaks(-bp, distance=max(1, min_distance), prominence=prominence)
    except Exception:
        return out

    if len(peaks) < 2 or len(troughs) < 2:
        return out

    systolic = bp[peaks]
    diastolic = bp[troughs]

    systolic = systolic[(systolic > 40) & (systolic < 250)]
    diastolic = diastolic[(diastolic > 20) & (diastolic < 180)]

    if len(systolic) == 0 or len(diastolic) == 0:
        return out

    sbp = np.mean(systolic)
    dbp = np.mean(diastolic)
    pulse_pressure = sbp - dbp
    map_est = dbp + pulse_pressure / 3

    out[f"{prefix}_systolic_mean"] = safe_float(sbp)
    out[f"{prefix}_diastolic_mean"] = safe_float(dbp)
    out[f"{prefix}_map_mean"] = safe_float(map_est)
    out[f"{prefix}_pulse_pressure_mean"] = safe_float(pulse_pressure)
    out[f"{prefix}_n_pulses"] = safe_float(len(systolic))

    return out


def derive_pleth_features(pleth, fs):
    out = {
        "derived_pleth_pulse_rate_bpm": np.nan,
        "derived_pleth_pulse_amplitude_mean": np.nan,
        "derived_pleth_n_pulses": np.nan,
    }

    pleth = np.asarray(pleth, dtype=float)
    pleth = pleth[~np.isnan(pleth)]

    if len(pleth) < fs * 5:
        return out

    pleth_centered = pleth - np.nanmedian(pleth)

    try:
        peaks, _ = find_peaks(
            pleth_centered,
            distance=max(1, int(0.3 * fs)),
            prominence=np.nanstd(pleth_centered) * 0.3,
        )
        troughs, _ = find_peaks(
            -pleth_centered,
            distance=max(1, int(0.3 * fs)),
            prominence=np.nanstd(pleth_centered) * 0.3,
        )
    except Exception:
        return out

    if len(peaks) < 2:
        return out

    rr = np.diff(peaks) / fs
    rr = rr[(rr > 60 / 220) & (rr < 60 / 30)]

    if len(rr) == 0:
        return out

    pulse_rate = 60 / rr

    amplitude = np.nan
    if len(troughs) > 0:
        amplitude = np.nanmedian(pleth_centered[peaks]) - np.nanmedian(
            pleth_centered[troughs]
        )

    out["derived_pleth_pulse_rate_bpm"] = safe_float(np.mean(pulse_rate))
    out["derived_pleth_pulse_amplitude_mean"] = safe_float(amplitude)
    out["derived_pleth_n_pulses"] = safe_float(len(peaks))

    return out


def derive_resp_features(resp, fs):
    out = {
        "derived_resp_rate_bpm": np.nan,
        "derived_resp_n_cycles": np.nan,
    }

    resp = np.asarray(resp, dtype=float)
    resp = resp[~np.isnan(resp)]

    if len(resp) < fs * 10:
        return out

    resp_centered = resp - np.nanmedian(resp)
    min_distance = int((60 / 40) * fs)

    try:
        peaks, _ = find_peaks(
            resp_centered,
            distance=max(1, min_distance),
            prominence=np.nanstd(resp_centered) * 0.3,
        )
    except Exception:
        return out

    if len(peaks) < 2:
        return out

    intervals = np.diff(peaks) / fs
    intervals = intervals[(intervals > 60 / 40) & (intervals < 60 / 5)]

    if len(intervals) == 0:
        return out

    rr = 60 / intervals

    out["derived_resp_rate_bpm"] = safe_float(np.mean(rr))
    out["derived_resp_n_cycles"] = safe_float(len(peaks))

    return out


def process_segment(segment_stem: Path, root: Path, window_seconds: float, min_valid_fraction: float):
    rows = []

    patient_id, study_id = infer_patient_and_study(segment_stem, root)

    match = SEGMENT_PATTERN.fullmatch(segment_stem.name)
    if not match:
        return rows

    record_id = match.group("record_id")
    segment_idx = int(match.group("segment_idx"))

    try:
        record = wfdb.rdrecord(str(segment_stem))
    except Exception:
        return rows

    x = getattr(record, "p_signal", None)
    if x is None:
        return rows

    x = np.asarray(x)
    fs = safe_float(getattr(record, "fs", None))

    if fs is None or fs <= 0:
        return rows

    segment_start_datetime = get_record_start_datetime(record)

    sig_names = list(getattr(record, "sig_name", None) or [])
    sig_names_clean = [sanitize_name(s) for s in sig_names]

    sig_len = x.shape[0]
    samples_per_window = max(1, int(round(window_seconds * fs)))
    n_windows = int(np.ceil(sig_len / samples_per_window))

    for w in range(n_windows):
        start_idx = w * samples_per_window
        end_idx = min((w + 1) * samples_per_window, sig_len)

        if end_idx <= start_idx:
            continue

        valid_fraction = (end_idx - start_idx) / samples_per_window
        if valid_fraction < min_valid_fraction:
            continue

        window_start_sec = start_idx / fs
        window_end_sec = end_idx / fs

        if segment_start_datetime is not None:
            window_start_datetime = segment_start_datetime + timedelta(seconds=window_start_sec)
            window_end_datetime = segment_start_datetime + timedelta(seconds=window_end_sec)
            segment_start_str = segment_start_datetime.isoformat()
            window_start_str = window_start_datetime.isoformat()
            window_end_str = window_end_datetime.isoformat()
        else:
            segment_start_str = None
            window_start_str = None
            window_end_str = None

        row = {
            "patient_id": patient_id,
            "study_id": study_id,
            "record_id": str(record_id),
            "segment_id": f"{record_id}_{segment_idx:04d}",
            "segment_index": str(segment_idx),
            "window_index": str(w),

            "segment_start_datetime": segment_start_str,
            "window_start_datetime": window_start_str,
            "window_end_datetime": window_end_str,
        }

        window = x[start_idx:end_idx, :]

        ecg_signal = None
        for candidate in ["ii", "v", "avr", "iii", "i"]:
            if candidate in sig_names_clean:
                ecg_signal = window[:, sig_names_clean.index(candidate)]
                break

        if ecg_signal is not None:
            row.update(derive_ecg_features(ecg_signal, fs))

        if "abp" in sig_names_clean:
            row.update(
                derive_pressure_features(
                    window[:, sig_names_clean.index("abp")],
                    fs,
                    "derived_abp",
                )
            )

        if "art" in sig_names_clean:
            row.update(
                derive_pressure_features(
                    window[:, sig_names_clean.index("art")],
                    fs,
                    "derived_art",
                )
            )

        if "pleth" in sig_names_clean:
            row.update(
                derive_pleth_features(
                    window[:, sig_names_clean.index("pleth")],
                    fs,
                )
            )

        if "resp" in sig_names_clean:
            row.update(
                derive_resp_features(
                    window[:, sig_names_clean.index("resp")],
                    fs,
                )
            )

        rows.append(row)

    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Add timestamps and derived physiological features from raw WFDB signals."
    )
    parser.add_argument("--waves-root", required=True, type=str)
    parser.add_argument("--base-csv", required=True, type=str)
    OUTPUT_FINAL_PATH = str(WORK_DIR / "output" / "03_mimic4_waveform_features_augmented.csv")
    parser.add_argument("--derived-csv", default=None, type=str)
    parser.add_argument("--window-seconds", default=30.0, type=float)
    parser.add_argument("--min-valid-fraction", default=0.8, type=float)
    parser.add_argument("--max-segments", default=None, type=int)

    args = parser.parse_args()

    root = Path(args.waves_root).resolve()

    print("Finding WFDB segments...")
    segments = find_segment_stems(root)

    if args.max_segments is not None:
        segments = segments[:args.max_segments]

    print(f"Found {len(segments)} segments")

    all_rows = []

    for stem in tqdm(segments, desc="Extracting timestamps + derived features"):
        all_rows.extend(
            process_segment(
                segment_stem=stem,
                root=root,
                window_seconds=args.window_seconds,
                min_valid_fraction=args.min_valid_fraction,
            )
        )

    derived_df = pd.DataFrame(all_rows)
    print(f"Derived/timestamp features shape: {derived_df.shape}")

    merge_keys = [
        "patient_id",
        "study_id",
        "record_id",
        "segment_id",
        "segment_index",
        "window_index",
    ]

    if derived_df.empty:
        print("WARNING: No derived features were generated.")
        derived_df = pd.DataFrame(columns=merge_keys)

    if args.derived_csv:
        derived_df.to_csv(args.derived_csv, index=False)
        print(f"Saved derived-only dataset to: {args.derived_csv}")

    print("Loading base feature dataset...")
    base_df = pd.read_csv(args.base_csv)
    print(f"Base shape: {base_df.shape}")

    for key in merge_keys:
        if key in base_df.columns:
            base_df[key] = base_df[key].astype(str)
        if key in derived_df.columns:
            derived_df[key] = derived_df[key].astype(str)

    print("Merging...")
    final_df = base_df.merge(derived_df, on=merge_keys, how="left")

    print(f"Final shape: {final_df.shape}")

    print("Saving augmented dataset...")
    final_df.to_csv(OUTPUT_FINAL_PATH, index=False)
    print(f"Saved augmented dataset to: {OUTPUT_FINAL_PATH}")


if __name__ == "__main__":
    main()  