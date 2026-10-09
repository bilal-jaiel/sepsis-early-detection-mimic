import os
import sys
import time
import subprocess
from pathlib import Path

import psycopg2


# ============================================================
# CONFIG
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "mimic_iv_clinical_hosp",
    "user": "postgres",
    "password": os.environ.get("MIMIC_DB_PASSWORD", ""),
}

BASE_DIR = Path(__file__).resolve().parent
APP_FILE = BASE_DIR / "app_new.py"
FORCE_REBUILD = False


# ============================================================
# HELPERS
# ============================================================

def connect():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def format_seconds(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}m {seconds}s"


def object_exists(cur, object_name):
    cur.execute("SELECT to_regclass(%s);", [object_name])
    return cur.fetchone()[0] is not None


def print_progress(done, total, label=""):
    percent = done / total
    bar_length = 30
    filled = int(bar_length * percent)
    bar = "█" * filled + "░" * (bar_length - filled)

    print(
        f"\r[{bar}] {percent * 100:5.1f}%  {label}",
        end="",
        flush=True,
    )

    if done == total:
        print()


def run_sql(cur, title, sql):
    print(f"\n▶ {title}")
    start = time.perf_counter()
    cur.execute(sql)
    print(f"  Done in {format_seconds(time.perf_counter() - start)}")


# ============================================================
# SQL BLOCKS
# ============================================================

SQL_DROP_OPTIMIZED_OBJECTS = """
DROP TABLE IF EXISTS cdm.dashboard_overview_stats;
DROP TABLE IF EXISTS cdm.dashboard_event_type_stats;
DROP TABLE IF EXISTS cdm.dashboard_top_concepts;
DROP TABLE IF EXISTS cdm.dashboard_waveform_concepts;
DROP TABLE IF EXISTS cdm.dashboard_patient_summary;
DROP TABLE IF EXISTS cdm.waveform_subject_mapping;
DROP MATERIALIZED VIEW IF EXISTS cdm.omop_longitudinal_events;
"""


SQL_CREATE_LONGITUDINAL_EVENTS = """
CREATE MATERIALIZED VIEW cdm.omop_longitudinal_events AS

SELECT
    m.measurement_id::bigint AS event_id,
    m.person_id,
    m.visit_occurrence_id,
    COALESCE(m.measurement_datetime, m.measurement_date::timestamp) AS event_datetime,
    'measurement' AS event_type,
    m.measurement_concept_id AS concept_id,
    c.concept_name,
    c.vocabulary_id,
    c.concept_code,
    m.value_as_number::double precision AS value_numeric,
    m.value_source_value::text AS value_text,
    m.unit_concept_id,
    COALESCE(u.concept_name, m.unit_source_value) AS unit_name,
    m.measurement_source_value AS source_value
FROM cdm.measurement m
LEFT JOIN cdm.concept c
    ON m.measurement_concept_id = c.concept_id
LEFT JOIN cdm.concept u
    ON m.unit_concept_id = u.concept_id

UNION ALL

SELECT
    o.observation_id::bigint AS event_id,
    o.person_id,
    o.visit_occurrence_id,
    COALESCE(o.observation_datetime, o.observation_date::timestamp) AS event_datetime,
    'observation' AS event_type,
    o.observation_concept_id AS concept_id,
    c.concept_name,
    c.vocabulary_id,
    c.concept_code,
    o.value_as_number::double precision AS value_numeric,
    o.value_as_string::text AS value_text,
    o.unit_concept_id,
    u.concept_name AS unit_name,
    o.observation_source_value AS source_value
FROM cdm.observation o
LEFT JOIN cdm.concept c
    ON o.observation_concept_id = c.concept_id
LEFT JOIN cdm.concept u
    ON o.unit_concept_id = u.concept_id

UNION ALL

SELECT
    de.drug_exposure_id::bigint AS event_id,
    de.person_id,
    de.visit_occurrence_id,
    COALESCE(de.drug_exposure_start_datetime, de.drug_exposure_start_date::timestamp) AS event_datetime,
    'drug_exposure' AS event_type,
    de.drug_concept_id AS concept_id,
    c.concept_name,
    c.vocabulary_id,
    c.concept_code,
    de.quantity::double precision AS value_numeric,
    de.sig::text AS value_text,
    NULL::integer AS unit_concept_id,
    de.dose_unit_source_value AS unit_name,
    de.drug_source_value AS source_value
FROM cdm.drug_exposure de
LEFT JOIN cdm.concept c
    ON de.drug_concept_id = c.concept_id

UNION ALL

SELECT
    co.condition_occurrence_id::bigint AS event_id,
    co.person_id,
    co.visit_occurrence_id,
    COALESCE(co.condition_start_datetime, co.condition_start_date::timestamp) AS event_datetime,
    'condition_occurrence' AS event_type,
    co.condition_concept_id AS concept_id,
    c.concept_name,
    c.vocabulary_id,
    c.concept_code,
    NULL::double precision AS value_numeric,
    co.condition_status_source_value::text AS value_text,
    NULL::integer AS unit_concept_id,
    NULL::text AS unit_name,
    co.condition_source_value AS source_value
FROM cdm.condition_occurrence co
LEFT JOIN cdm.concept c
    ON co.condition_concept_id = c.concept_id

UNION ALL

SELECT
    po.procedure_occurrence_id::bigint AS event_id,
    po.person_id,
    po.visit_occurrence_id,
    COALESCE(po.procedure_datetime, po.procedure_date::timestamp) AS event_datetime,
    'procedure_occurrence' AS event_type,
    po.procedure_concept_id AS concept_id,
    c.concept_name,
    c.vocabulary_id,
    c.concept_code,
    po.quantity::double precision AS value_numeric,
    NULL::text AS value_text,
    NULL::integer AS unit_concept_id,
    NULL::text AS unit_name,
    po.procedure_source_value AS source_value
FROM cdm.procedure_occurrence po
LEFT JOIN cdm.concept c
    ON po.procedure_concept_id = c.concept_id;
"""


SQL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ole_person_id
ON cdm.omop_longitudinal_events(person_id);

CREATE INDEX IF NOT EXISTS idx_ole_event_datetime
ON cdm.omop_longitudinal_events(event_datetime);

CREATE INDEX IF NOT EXISTS idx_ole_event_type
ON cdm.omop_longitudinal_events(event_type);

CREATE INDEX IF NOT EXISTS idx_ole_concept_id
ON cdm.omop_longitudinal_events(concept_id);

CREATE INDEX IF NOT EXISTS idx_ole_person_datetime
ON cdm.omop_longitudinal_events(person_id, event_datetime);

CREATE INDEX IF NOT EXISTS idx_waveform_person_concept
ON cdm.omop_longitudinal_events(person_id, concept_name, event_datetime);

CREATE INDEX IF NOT EXISTS idx_ole_event_type_concept
ON cdm.omop_longitudinal_events(event_type, concept_name);

CREATE INDEX IF NOT EXISTS idx_ole_vocab_person_time
ON cdm.omop_longitudinal_events(vocabulary_id, person_id, event_datetime);
"""


SQL_DASHBOARD_OVERVIEW_STATS = """
CREATE TABLE cdm.dashboard_overview_stats AS
SELECT 'Patients' AS label, COUNT(DISTINCT person_id) AS value
FROM cdm.omop_longitudinal_events

UNION ALL

SELECT 'Events', COUNT(*)
FROM cdm.omop_longitudinal_events

UNION ALL

SELECT 'Waveform Events', COUNT(*)
FROM cdm.omop_longitudinal_events
WHERE vocabulary_id = 'MIMIC-Wave-Derived'

UNION ALL

SELECT 'Concepts', COUNT(DISTINCT concept_name)
FROM cdm.omop_longitudinal_events;
"""


SQL_DASHBOARD_EVENT_TYPE_STATS = """
CREATE TABLE cdm.dashboard_event_type_stats AS
SELECT
    event_type,
    COUNT(*) AS n_events
FROM cdm.omop_longitudinal_events
GROUP BY event_type;
"""


SQL_DASHBOARD_TOP_CONCEPTS = """
DROP TABLE IF EXISTS cdm.dashboard_top_concepts;

CREATE TABLE cdm.dashboard_top_concepts AS
SELECT
    cleaned_concept_name AS concept_name,
    event_type,
    vocabulary_id,
    COUNT(*) AS n_events
FROM (
    SELECT
        e.event_type,

        CASE
            WHEN e.event_type = 'condition_occurrence'
            THEN COALESCE(
                c_icd.concept_name,
                NULLIF(e.source_value, ''),
                'Unknown condition'
            )

            WHEN e.event_type = 'drug_exposure'
                 AND e.concept_name = 'No matching concept'
                 AND e.source_value ~ '^[0-9]+$'
            THEN COALESCE(
                c_ndc.concept_name,
                CONCAT('Rx NDC: ', e.source_value)
            )

            WHEN e.concept_name LIKE 'label:[%]%'
            THEN substring(e.concept_name FROM 'label:\\[([^\\]]+)\\]')

            WHEN e.concept_name = 'No matching concept'
            THEN COALESCE(
                NULLIF(e.source_value, ''),
                'Unknown concept'
            )

            ELSE e.concept_name
        END AS cleaned_concept_name,

        CASE
            WHEN e.event_type = 'condition_occurrence'
            THEN COALESCE(c_icd.vocabulary_id, e.vocabulary_id)

            WHEN e.event_type = 'drug_exposure'
                 AND e.concept_name = 'No matching concept'
                 AND e.source_value ~ '^[0-9]+$'
            THEN COALESCE(c_ndc.vocabulary_id, e.vocabulary_id)

            ELSE e.vocabulary_id
        END AS vocabulary_id

    FROM cdm.omop_longitudinal_events e

    LEFT JOIN cdm.concept c_icd
        ON e.event_type = 'condition_occurrence'
       AND REPLACE(c_icd.concept_code, '.', '') = e.source_value
       AND c_icd.vocabulary_id IN ('ICD9CM', 'ICD10CM')

    LEFT JOIN cdm.concept c_ndc
        ON e.event_type = 'drug_exposure'
       AND c_ndc.concept_code = e.source_value
       AND c_ndc.vocabulary_id IN ('NDC', 'RxNorm', 'RxNorm Extension')
) x
WHERE cleaned_concept_name IS NOT NULL
GROUP BY cleaned_concept_name, event_type, vocabulary_id;
"""


SQL_DASHBOARD_WAVEFORM_CONCEPTS = """
CREATE TABLE cdm.dashboard_waveform_concepts AS
SELECT DISTINCT
    concept_name
FROM cdm.omop_longitudinal_events
WHERE vocabulary_id = 'MIMIC-Wave-Derived'
  AND concept_name IS NOT NULL;
"""


SQL_WAVEFORM_SUBJECT_MAPPING = """
CREATE TABLE cdm.waveform_subject_mapping AS
SELECT
    w.subject_id,
    p.person_id AS omop_person_id,
    p.person_source_value,
    CASE WHEN p.person_id IS NULL THEN FALSE ELSE TRUE END AS has_omop_mapping
FROM (
    SELECT DISTINCT person_id AS subject_id
    FROM cdm.omop_longitudinal_events
    WHERE vocabulary_id = 'MIMIC-Wave-Derived'
) w
LEFT JOIN cdm.person p
    ON w.subject_id::text = p.person_source_value;

CREATE INDEX IF NOT EXISTS idx_waveform_subject_mapping_subject
ON cdm.waveform_subject_mapping(subject_id);

CREATE INDEX IF NOT EXISTS idx_waveform_subject_mapping_omop
ON cdm.waveform_subject_mapping(omop_person_id);
"""


SQL_DASHBOARD_PATIENT_SUMMARY = """
CREATE TABLE cdm.dashboard_patient_summary AS
WITH clinical AS (
    SELECT
        p.person_source_value::bigint AS display_patient_id,
        p.person_id AS omop_person_id,
        TRUE AS has_omop_mapping
    FROM cdm.person p
    WHERE p.person_source_value ~ '^[0-9]+$'
),
waveform AS (
    SELECT DISTINCT
        person_id::bigint AS display_patient_id
    FROM cdm.omop_longitudinal_events
    WHERE vocabulary_id = 'MIMIC-Wave-Derived'
)
SELECT
    COALESCE(c.display_patient_id, w.display_patient_id) AS display_patient_id,
    c.omop_person_id,
    COALESCE(c.has_omop_mapping, FALSE) AS has_omop_mapping,
    w.display_patient_id IS NOT NULL AS has_waveform
FROM clinical c
FULL OUTER JOIN waveform w
    ON c.display_patient_id = w.display_patient_id;

CREATE INDEX IF NOT EXISTS idx_dashboard_patient_summary_display
ON cdm.dashboard_patient_summary(display_patient_id);

CREATE INDEX IF NOT EXISTS idx_dashboard_patient_summary_waveform
ON cdm.dashboard_patient_summary(has_waveform);

CREATE INDEX IF NOT EXISTS idx_dashboard_patient_summary_display_omop
ON cdm.dashboard_patient_summary(display_patient_id, omop_person_id);
"""


SQL_NOTE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_note_person_datetime
ON cdm.note(person_id, note_datetime DESC);
"""


SQL_CHECK = """
SELECT label, value
FROM cdm.dashboard_overview_stats
ORDER BY label;
"""


# ============================================================
# OPTIMIZATION
# ============================================================

def optimize_database():
    print("Connecting to PostgreSQL...")
    start_total = time.perf_counter()

    with connect() as conn:
        with conn.cursor() as cur:

            tasks = []

            if FORCE_REBUILD:
                tasks.append((
                    "Force rebuild: dropping optimized objects",
                    SQL_DROP_OPTIMIZED_OBJECTS,
                    True,
                ))

            tasks.append((
                "Creating cdm.omop_longitudinal_events if missing",
                SQL_CREATE_LONGITUDINAL_EVENTS,
                not object_exists(cur, "cdm.omop_longitudinal_events"),
            ))

            tasks.append((
                "Creating missing indexes",
                SQL_INDEXES,
                True,
            ))

            dashboard_tasks = [
                ("cdm.dashboard_overview_stats", "Creating dashboard_overview_stats", SQL_DASHBOARD_OVERVIEW_STATS),
                ("cdm.dashboard_event_type_stats", "Creating dashboard_event_type_stats", SQL_DASHBOARD_EVENT_TYPE_STATS),
                ("cdm.dashboard_top_concepts", "Creating dashboard_top_concepts", SQL_DASHBOARD_TOP_CONCEPTS),
                ("cdm.dashboard_waveform_concepts", "Creating dashboard_waveform_concepts", SQL_DASHBOARD_WAVEFORM_CONCEPTS),
                ("cdm.waveform_subject_mapping", "Creating waveform_subject_mapping", SQL_WAVEFORM_SUBJECT_MAPPING),
                ("cdm.dashboard_patient_summary", "Creating dashboard_patient_summary", SQL_DASHBOARD_PATIENT_SUMMARY),
            ]

            for object_name, title, sql in dashboard_tasks:
                tasks.append((
                    f"{title} if missing",
                    sql,
                    not object_exists(cur, object_name),
                ))

            tasks.append((
                "Creating note indexes",
                SQL_NOTE_INDEXES,
                True,
            ))

            total = len(tasks)
            completed = 0

            print("\nOptimization progress:")
            print_progress(completed, total, "Starting...")

            for title, sql, should_run in tasks:
                completed += 1

                if should_run:
                    print_progress(completed - 1, total, title)
                    step_start = time.perf_counter()
                    cur.execute(sql)
                    elapsed = format_seconds(time.perf_counter() - step_start)
                    print_progress(completed, total, f"{title} — done in {elapsed}")
                else:
                    print_progress(completed, total, f"{title} — already exists")

            print("\nChecking dashboard stats...")
            cur.execute(SQL_CHECK)
            rows = cur.fetchall()

    print("\nOptimization check completed.")
    for label, value in rows:
        print(f"- {label}: {value:,}")

    print(f"\nTotal optimization time: {format_seconds(time.perf_counter() - start_total)}")


# ============================================================
# STREAMLIT LAUNCH
# ============================================================

def launch_streamlit():
    if not APP_FILE.exists():
        raise FileNotFoundError(f"Cannot find Streamlit app file: {APP_FILE.resolve()}")

    print("\nLaunching Streamlit app...")
    print(f"App file: {APP_FILE.resolve()}")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(APP_FILE),
        ],
        check=True,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    optimize_database()
    launch_streamlit()


if __name__ == "__main__":
    main()