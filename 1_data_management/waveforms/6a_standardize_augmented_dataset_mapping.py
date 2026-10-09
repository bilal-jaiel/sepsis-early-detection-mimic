import os
from pathlib import Path

# Working directory for intermediate files (git-ignored), override with WAVEFORM_WORKDIR
WORK_DIR = Path(os.environ.get("WAVEFORM_WORKDIR", Path(__file__).resolve().parents[2] / "data" / "waveforms"))

import pandas as pd
from tqdm import tqdm

INPUT_PATH = str(WORK_DIR / "output" / "03_mimic4_waveform_features_augmented.csv")

OUTPUT_DATASET = str(WORK_DIR / "output" / "03b_wfdb_augmented_standard_names.csv")
OUTPUT_MAPPING = str(WORK_DIR / "output" / "03b_wfdb_augmented_feature_mapping.csv")

signal_names = {
    "ii": "ecg_lead_ii",
    "v": "ecg_lead_v",
    "avr": "ecg_lead_avr",
    "iii": "ecg_lead_iii",
    "pleth": "photoplethysmography",
    "resp": "respiration",
    "abp": "arterial_blood_pressure",
    "art": "arterial_pressure",
    "cvp": "central_venous_pressure",
}

signal_units = {
    "ii": "mV",
    "v": "mV",
    "avr": "mV",
    "iii": "mV",
    "pleth": "arbitrary_unit",
    "resp": "arbitrary_unit",
    "abp": "mmHg",
    "art": "mmHg",
    "cvp": "mmHg",
}

signal_loinc = {
    "ii": ("131328-9", "ECG study"),
    "v": ("131328-9", "ECG study"),
    "avr": ("131328-9", "ECG study"),
    "iii": ("131328-9", "ECG study"),
    "abp": ("8478-0", "Mean blood pressure"),
    "art": ("8478-0", "Mean blood pressure"),
    "cvp": ("8591-9", "Central venous pressure"),
    "resp": ("9279-1", "Respiratory rate"),
    "pleth": ("59408-5", "Pulse oximetry waveform"),
}

stat_descriptions = {
    "mean": "Mean value within the time window",
    "std": "Standard deviation within the time window",
    "min": "Minimum value within the time window",
    "max": "Maximum value within the time window",
    "median": "Median value within the time window",
    "p10": "10th percentile within the time window",
    "p25": "25th percentile within the time window",
    "p75": "75th percentile within the time window",
    "p90": "90th percentile within the time window",
    "rms": "Root mean square within the time window",
    "iqr": "Interquartile range within the time window",
    "range": "Maximum minus minimum value within the time window",
    "abs_mean": "Mean absolute value within the time window",
    "diff_mean": "Mean of consecutive sample differences",
    "diff_std": "Standard deviation of consecutive sample differences",
    "zero_crossings": "Number of zero crossings after mean centering",
    "missing_ratio": "Fraction of missing samples within the time window",
}

derived_mapping = {
    "derived_ecg_hr_mean_bpm": ("ecg_heart_rate_mean_bpm", "ECG", "Heart rate derived from ECG R-peaks", "beats/min", "8867-4", "Heart rate"),
    "derived_ecg_hr_std_bpm": ("ecg_heart_rate_std_bpm", "ECG", "Standard deviation of heart rate derived from ECG", "beats/min", "8867-4", "Heart rate"),
    "derived_ecg_hrv_sdnn_ms": ("ecg_hrv_sdnn_ms", "ECG", "Heart rate variability SDNN derived from RR intervals", "ms", "", ""),
    "derived_ecg_hrv_rmssd_ms": ("ecg_hrv_rmssd_ms", "ECG", "Heart rate variability RMSSD derived from RR intervals", "ms", "", ""),
    "derived_ecg_n_beats": ("ecg_number_of_detected_beats", "ECG", "Number of detected ECG beats in the window", "count", "", ""),

    "derived_pleth_pulse_rate_bpm": ("pleth_pulse_rate_bpm", "PLETH", "Pulse rate derived from photoplethysmography", "beats/min", "8867-4", "Heart rate"),
    "derived_pleth_pulse_amplitude_mean": ("pleth_pulse_amplitude_mean", "PLETH", "Mean pulse amplitude derived from PPG waveform", "arbitrary_unit", "", ""),
    "derived_pleth_n_pulses": ("pleth_number_of_detected_pulses", "PLETH", "Number of detected PPG pulses in the window", "count", "", ""),

    "derived_resp_rate_bpm": ("respiratory_rate_bpm", "RESP", "Respiratory rate derived from respiration waveform", "breaths/min", "9279-1", "Respiratory rate"),
    "derived_resp_n_cycles": ("respiration_number_of_detected_cycles", "RESP", "Number of detected respiratory cycles in the window", "count", "", ""),

    "derived_abp_systolic_mean": ("arterial_blood_pressure_systolic_mean", "ABP", "Mean systolic arterial blood pressure derived from ABP waveform", "mmHg", "8480-6", "Systolic blood pressure"),
    "derived_abp_diastolic_mean": ("arterial_blood_pressure_diastolic_mean", "ABP", "Mean diastolic arterial blood pressure derived from ABP waveform", "mmHg", "8462-4", "Diastolic blood pressure"),
    "derived_abp_map_mean": ("arterial_blood_pressure_map_mean", "ABP", "Mean arterial pressure derived from ABP waveform", "mmHg", "8478-0", "Mean blood pressure"),
    "derived_abp_pulse_pressure_mean": ("arterial_blood_pressure_pulse_pressure_mean", "ABP", "Mean pulse pressure derived from ABP waveform", "mmHg", "", ""),
    "derived_abp_n_pulses": ("arterial_blood_pressure_number_of_detected_pulses", "ABP", "Number of detected ABP pulses", "count", "", ""),

    "derived_art_systolic_mean": ("arterial_pressure_systolic_mean", "ART", "Mean systolic arterial pressure derived from ART waveform", "mmHg", "8480-6", "Systolic blood pressure"),
    "derived_art_diastolic_mean": ("arterial_pressure_diastolic_mean", "ART", "Mean diastolic arterial pressure derived from ART waveform", "mmHg", "8462-4", "Diastolic blood pressure"),
    "derived_art_map_mean": ("arterial_pressure_map_mean", "ART", "Mean arterial pressure derived from ART waveform", "mmHg", "8478-0", "Mean blood pressure"),
    "derived_art_pulse_pressure_mean": ("arterial_pressure_pulse_pressure_mean", "ART", "Mean pulse pressure derived from ART waveform", "mmHg", "", ""),
    "derived_art_n_pulses": ("arterial_pressure_number_of_detected_pulses", "ART", "Number of detected ART pulses", "count", "", ""),
}

print("Loading dataset...")
df = pd.read_csv(INPUT_PATH)
print(f"Input shape: {df.shape}")

rename_dict = {}
mapping_rows = []

for col in df.columns:

    if col.startswith("sig_") and "__" in col:
        left, stat = col.split("__", 1)
        signal = left.replace("sig_", "")

        standard_signal = signal_names.get(signal, signal)
        standard_name = f"{standard_signal}_{stat}"

        loinc_code, loinc_name = signal_loinc.get(signal, ("", ""))

        rename_dict[col] = standard_name

        mapping_rows.append({
            "original_name": col,
            "standard_name": standard_name,
            "category": "raw_signal_statistical_feature",
            "signal_original": signal,
            "signal_standard": standard_signal,
            "statistic": stat,
            "description": stat_descriptions.get(stat, ""),
            "unit": signal_units.get(signal, ""),
            "loinc_code": loinc_code,
            "loinc_name": loinc_name,
            "loinc_mapping_level": "signal_level",
            "mapping_status": "signal_level_mapping",
            "notes": "LOINC refers to the underlying physiological signal, not to the derived statistic itself."
        })

    elif col in derived_mapping:
        standard_name, signal, description, unit, loinc_code, loinc_name = derived_mapping[col]

        rename_dict[col] = standard_name

        mapping_rows.append({
            "original_name": col,
            "standard_name": standard_name,
            "category": "derived_physiological_feature",
            "signal_original": signal,
            "signal_standard": signal,
            "statistic": "",
            "description": description,
            "unit": unit,
            "loinc_code": loinc_code,
            "loinc_name": loinc_name,
            "loinc_mapping_level": "measurement_level" if loinc_code else "",
            "mapping_status": "mapped" if loinc_code else "derived_feature_no_direct_loinc",
            "notes": "Derived physiological feature computed from waveform signal."
        })

    else:
        rename_dict[col] = col

        mapping_rows.append({
            "original_name": col,
            "standard_name": col,
            "category": "identifier_or_metadata",
            "signal_original": "",
            "signal_standard": "",
            "statistic": "",
            "description": "Identifier, metadata, timestamp, or signal availability flag",
            "unit": "",
            "loinc_code": "",
            "loinc_name": "",
            "loinc_mapping_level": "",
            "mapping_status": "not_applicable",
            "notes": "Non-signal feature."
        })

df_renamed = df.rename(columns=rename_dict)
mapping_df = pd.DataFrame(mapping_rows)

print(f"Output shape: {df_renamed.shape}")

print("Saving standardized dataset...")
chunk_size = 10000

with open(OUTPUT_DATASET, "w", newline="", encoding="utf-8") as f:
    df_renamed.iloc[:0].to_csv(f, index=False)

    for i in tqdm(range(0, len(df_renamed), chunk_size), desc="Saving CSV"):
        df_renamed.iloc[i:i + chunk_size].to_csv(f, index=False, header=False)

mapping_df.to_csv(OUTPUT_MAPPING, index=False)

print("Done.")
print(f"Saved standardized dataset to: {OUTPUT_DATASET}")
print(f"Saved mapping dictionary to: {OUTPUT_MAPPING}")