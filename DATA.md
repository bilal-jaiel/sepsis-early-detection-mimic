# Data

No patient data is stored in this repository, and none may be: MIMIC-IV is distributed under the PhysioNet Credentialed Health Data License (see the license page of each dataset below), which forbids sharing the data or giving access to it. Every intermediate file (CSV, NPZ, parquet, trained model) is listed in `.gitignore`.

## Getting access

1. Create a PhysioNet account and complete the required human-subjects training (CITI "Data or Specimens Only Research").
2. Request credentialed access and sign the data use agreement for each dataset below.

| Dataset | Version used | Used for |
|---|---|---|
| [MIMIC-IV](https://physionet.org/content/mimiciv/) | 3.1 | `hosp` and `icu` modules, OMOP ETL, sepsis cohort |
| [MIMIC-IV-Note](https://physionet.org/content/mimic-iv-note/) | 2.2 | discharge summaries and radiology reports |
| [MIMIC-IV Waveform Database](https://physionet.org/content/mimic4wdb/) | 0.1.0 (preview) | bedside waveform features |

## Expected layout

The scripts and notebooks read and write under a local `data/` folder at the repository root, which git ignores:

```
data/
├── mimic-iv-3.1/                     hosp/ and icu/ CSV files
├── mimic-iv-note-deidentified-free-text-clinical-notes-2.2/note/
├── duckdb/                           DuckDB files used for the ICU exploration
├── waveforms/output/                 waveform feature tables
├── free_text_clinical_notes.csv.gz   cleaned notes (notebook 1_data_management/clinical_notes)
├── X_tfidf.npz                       TF-IDF matrix (notebook 2_data_exchange_omop/clinical_notes)
├── X_structured.csv, y_sepsis.csv    model inputs (3_sepsis_model/build_sepsis_dataset.ipynb)
└── X_tfidf_final.npz
```

The OMOP CDM database itself lives in a local PostgreSQL instance; set its password in a `.env` file (see `.env.example`).
