import os

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "mimic_iv_clinical_hosp",
    "user": "postgres",
    "password": os.environ.get("MIMIC_DB_PASSWORD", ""),
}