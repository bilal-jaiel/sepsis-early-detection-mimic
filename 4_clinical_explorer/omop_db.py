import time
import pandas as pd
import psycopg2
from config import DB_CONFIG


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def run_query(query, params=None):
    if params is None:
        params = []

    start = time.perf_counter()

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)

    elapsed = time.perf_counter() - start
    return df, elapsed


def get_overview_counts():
    query = """
        SELECT label, value
        FROM cdm.dashboard_overview_stats
        ORDER BY label;
    """
    return run_query(query)


def get_event_type_distribution():
    query = """
        SELECT event_type, n_events
        FROM cdm.dashboard_event_type_stats
        ORDER BY n_events DESC;
    """
    return run_query(query)


def get_top_concepts(limit=20):
    query = """
        SELECT
            concept_name,
            event_type,
            vocabulary_id,
            n_events
        FROM cdm.dashboard_top_concepts
        WHERE concept_name IS NOT NULL
          AND concept_name <> 'No matching concept'
          AND concept_name <> 'Unknown concept'
        ORDER BY n_events DESC
        LIMIT %s;
    """
    return run_query(query, [limit])


def get_all_patient_selector_options(limit=1000):
    query = """
        SELECT
            display_patient_id,
            has_waveform,
            omop_person_id,
            has_omop_mapping
        FROM cdm.dashboard_patient_summary
        WHERE has_omop_mapping = TRUE
        ORDER BY has_waveform DESC, display_patient_id
        LIMIT %s;
    """
    return run_query(query, [limit])


def get_patient_demographics_by_subject(subject_id):
    query = """
        SELECT
            p.person_id AS omop_person_id,
            p.person_source_value AS subject_id,
            p.year_of_birth,
            p.gender_source_value,
            p.race_source_value,
            p.ethnicity_source_value
        FROM cdm.dashboard_patient_summary s
        JOIN cdm.person p
            ON s.omop_person_id = p.person_id
        WHERE s.display_patient_id = %s
          AND s.has_omop_mapping = TRUE;
    """
    return run_query(query, [subject_id])


def get_patient_summary_by_subject(subject_id):
    query = """
        SELECT
            person_id AS subject_id,
            COUNT(*) AS total_events,
            COUNT(DISTINCT visit_occurrence_id) AS visits,
            MIN(event_datetime) AS first_event,
            MAX(event_datetime) AS last_event,
            COUNT(DISTINCT concept_name) AS concepts,
            COUNT(*) FILTER (
                WHERE vocabulary_id = 'MIMIC-Wave-Derived'
            ) AS waveform_events,
            COUNT(*) FILTER (
                WHERE vocabulary_id IS DISTINCT FROM 'MIMIC-Wave-Derived'
            ) AS non_waveform_events
        FROM cdm.omop_longitudinal_events
        WHERE person_id = %s
        GROUP BY person_id;
    """
    return run_query(query, [subject_id])


def get_patient_clinical_counts(subject_id):
    query = """
        WITH selected_patient AS (
            SELECT omop_person_id
            FROM cdm.dashboard_patient_summary
            WHERE display_patient_id = %s
              AND has_omop_mapping = TRUE
        )
        SELECT 'Visits' AS label, COUNT(*) AS value
        FROM cdm.visit_occurrence v
        JOIN selected_patient s ON v.person_id = s.omop_person_id

        UNION ALL

        SELECT 'Care units', COUNT(*)
        FROM cdm.visit_detail vd
        JOIN selected_patient s ON vd.person_id = s.omop_person_id

        UNION ALL

        SELECT 'Medications', COUNT(*)
        FROM cdm.drug_exposure d
        JOIN selected_patient s ON d.person_id = s.omop_person_id

        UNION ALL

        SELECT 'Conditions', COUNT(*)
        FROM cdm.condition_occurrence c
        JOIN selected_patient s ON c.person_id = s.omop_person_id

        UNION ALL

        SELECT 'Procedures', COUNT(*)
        FROM cdm.procedure_occurrence p
        JOIN selected_patient s ON p.person_id = s.omop_person_id

        UNION ALL

        SELECT 'Measurements', COUNT(*)
        FROM cdm.measurement m
        JOIN selected_patient s ON m.person_id = s.omop_person_id

        UNION ALL

        SELECT 'Observations', COUNT(*)
        FROM cdm.observation o
        JOIN selected_patient s ON o.person_id = s.omop_person_id

        UNION ALL

        SELECT 'Doctor notes', COUNT(*)
        FROM cdm.note n
        JOIN selected_patient s ON n.person_id = s.omop_person_id;
    """
    return run_query(query, [subject_id])


def get_patient_visits_by_subject(subject_id):
    query = """
        SELECT
            v.visit_source_value,
            v.visit_occurrence_id,
            v.visit_start_datetime,
            v.visit_end_datetime
        FROM cdm.dashboard_patient_summary s
        JOIN cdm.visit_occurrence v
            ON s.omop_person_id = v.person_id
        WHERE s.display_patient_id = %s
          AND s.has_omop_mapping = TRUE
        ORDER BY v.visit_start_datetime ASC
        LIMIT 500;
    """
    return run_query(query, [subject_id])


def get_patient_timeline(person_id, event_types, limit=500, start_datetime=None, end_datetime=None):
    query = """
        WITH selected_patient AS (
            SELECT display_patient_id, omop_person_id
            FROM cdm.dashboard_patient_summary
            WHERE display_patient_id = %s
              AND has_omop_mapping = TRUE
        )
        SELECT *
        FROM (
            SELECT
                v.visit_start_datetime AS event_datetime,
                'admission' AS event_type,
                'Hospital admission' AS concept_name,
                'OMOP visit_occurrence' AS vocabulary_id,
                NULL AS concept_code,
                NULL::numeric AS value_numeric,
                v.visit_source_value AS value_text,
                NULL AS unit_name,
                v.visit_source_value AS source_value,
                v.visit_occurrence_id
            FROM selected_patient s
            JOIN cdm.visit_occurrence v ON s.omop_person_id = v.person_id

            UNION ALL

            SELECT
                v.visit_end_datetime AS event_datetime,
                'discharge' AS event_type,
                'Hospital discharge' AS concept_name,
                'OMOP visit_occurrence' AS vocabulary_id,
                NULL AS concept_code,
                NULL::numeric AS value_numeric,
                v.visit_source_value AS value_text,
                NULL AS unit_name,
                v.visit_source_value AS source_value,
                v.visit_occurrence_id
            FROM selected_patient s
            JOIN cdm.visit_occurrence v ON s.omop_person_id = v.person_id
            WHERE v.visit_end_datetime IS NOT NULL

            UNION ALL

            SELECT
                vd.visit_detail_start_datetime AS event_datetime,
                'care_unit_start' AS event_type,
                COALESCE(vd.visit_detail_source_value, 'Care unit start') AS concept_name,
                'OMOP visit_detail' AS vocabulary_id,
                NULL AS concept_code,
                NULL::numeric AS value_numeric,
                vd.visit_detail_source_value AS value_text,
                NULL AS unit_name,
                vd.visit_detail_source_value AS source_value,
                vd.visit_occurrence_id
            FROM selected_patient s
            JOIN cdm.visit_detail vd ON s.omop_person_id = vd.person_id

            UNION ALL

            SELECT
                vd.visit_detail_end_datetime AS event_datetime,
                'care_unit_end' AS event_type,
                COALESCE(vd.visit_detail_source_value, 'Care unit end') AS concept_name,
                'OMOP visit_detail' AS vocabulary_id,
                NULL AS concept_code,
                NULL::numeric AS value_numeric,
                vd.visit_detail_source_value AS value_text,
                NULL AS unit_name,
                vd.visit_detail_source_value AS source_value,
                vd.visit_occurrence_id
            FROM selected_patient s
            JOIN cdm.visit_detail vd ON s.omop_person_id = vd.person_id
            WHERE vd.visit_detail_end_datetime IS NOT NULL

            UNION ALL

            SELECT
                d.drug_exposure_start_datetime AS event_datetime,
                'drug_exposure' AS event_type,
                CASE
                    WHEN d.drug_concept_id IS NOT NULL
                         AND d.drug_concept_id != 0
                         AND c_standard.concept_name IS NOT NULL
                         AND c_standard.concept_name != 'No matching concept'
                    THEN c_standard.concept_name

                    WHEN d.drug_source_value ~ '^[0-9]+$'
                    THEN COALESCE(
                        c_ndc.concept_name,
                        CONCAT('Rx NDC: ', d.drug_source_value)
                    )

                    ELSE COALESCE(
                        NULLIF(d.drug_source_value, ''),
                        NULLIF(c_source.concept_name, 'No matching concept'),
                        'Unknown medication'
                    )
                END AS concept_name,
                'OMOP drug_exposure' AS vocabulary_id,
                d.drug_source_value AS concept_code,
                d.quantity AS value_numeric,
                d.dose_unit_source_value AS value_text,
                d.dose_unit_source_value AS unit_name,
                d.drug_source_value AS source_value,
                d.visit_occurrence_id
            FROM selected_patient s
            JOIN cdm.drug_exposure d ON s.omop_person_id = d.person_id
            LEFT JOIN cdm.concept c_standard ON d.drug_concept_id = c_standard.concept_id
            LEFT JOIN cdm.concept c_source ON d.drug_source_concept_id = c_source.concept_id
            LEFT JOIN cdm.concept c_ndc
                ON c_ndc.concept_code = d.drug_source_value
               AND c_ndc.vocabulary_id IN ('NDC', 'RxNorm', 'RxNorm Extension')

            UNION ALL

            SELECT
                co.condition_start_datetime AS event_datetime,
                'condition_occurrence' AS event_type,
                COALESCE(
                    c_icd.concept_name,
                    NULLIF(co.condition_source_value, ''),
                    'Unknown condition'
                ) AS concept_name,
                COALESCE(c_icd.vocabulary_id, 'OMOP condition_occurrence') AS vocabulary_id,
                co.condition_source_value AS concept_code,
                NULL::numeric AS value_numeric,
                NULL AS value_text,
                NULL AS unit_name,
                co.condition_source_value AS source_value,
                co.visit_occurrence_id
            FROM selected_patient s
            JOIN cdm.condition_occurrence co ON s.omop_person_id = co.person_id
            LEFT JOIN cdm.concept c_icd
                ON REPLACE(c_icd.concept_code, '.', '') = co.condition_source_value
               AND c_icd.vocabulary_id IN ('ICD9CM', 'ICD10CM')

            UNION ALL

            SELECT
                po.procedure_datetime AS event_datetime,
                'procedure_occurrence' AS event_type,
                COALESCE(
                    c_proc.concept_name,
                    NULLIF(c1.concept_name, 'No matching concept'),
                    NULLIF(c2.concept_name, 'No matching concept'),
                    po.procedure_source_value,
                    'Procedure'
                ) AS concept_name,
                COALESCE(c_proc.vocabulary_id, 'OMOP procedure_occurrence') AS vocabulary_id,
                po.procedure_source_value AS concept_code,
                NULL::numeric AS value_numeric,
                NULL AS value_text,
                NULL AS unit_name,
                po.procedure_source_value AS source_value,
                po.visit_occurrence_id
            FROM selected_patient s
            JOIN cdm.procedure_occurrence po ON s.omop_person_id = po.person_id
            LEFT JOIN cdm.concept c1 ON po.procedure_concept_id = c1.concept_id
            LEFT JOIN cdm.concept c2 ON po.procedure_source_concept_id = c2.concept_id
            LEFT JOIN cdm.concept c_proc
                ON REPLACE(c_proc.concept_code, '.', '') = po.procedure_source_value
               AND c_proc.vocabulary_id IN ('ICD9Proc', 'ICD10PCS', 'CPT4', 'HCPCS')

            UNION ALL

            SELECT
                m.measurement_datetime AS event_datetime,
                'measurement' AS event_type,

                COALESCE(
                    NULLIF(m.measurement_source_value, ''),
                    CASE
                        WHEN COALESCE(c1.concept_name, c2.concept_name) LIKE 'label:[%%]%%'
                        THEN substring(
                            COALESCE(c1.concept_name, c2.concept_name)
                            FROM 'label:\\[([^\\]]+)\\]'
                        )
                    END,
                    NULLIF(c1.concept_name, 'No matching concept'),
                    NULLIF(c2.concept_name, 'No matching concept'),
                    'Measurement'
                ) AS concept_name,

                'OMOP measurement' AS vocabulary_id,

                COALESCE(
                    NULLIF(c1.concept_name, 'No matching concept'),
                    NULLIF(c2.concept_name, 'No matching concept'),
                    m.measurement_source_value
                ) AS concept_code,

                m.value_as_number AS value_numeric,
                m.value_source_value AS value_text,
                m.unit_source_value AS unit_name,

                COALESCE(
                    NULLIF(c1.concept_name, 'No matching concept'),
                    NULLIF(c2.concept_name, 'No matching concept'),
                    m.measurement_source_value
                ) AS source_value,

                m.visit_occurrence_id
            FROM selected_patient s
            JOIN cdm.measurement m ON s.omop_person_id = m.person_id
            LEFT JOIN cdm.concept c1 ON m.measurement_concept_id = c1.concept_id
            LEFT JOIN cdm.concept c2 ON m.measurement_source_concept_id = c2.concept_id
        ) x
        WHERE event_datetime IS NOT NULL
          AND event_type = ANY(%s)
          AND (%s IS NULL OR event_datetime >= %s)
          AND (%s IS NULL OR event_datetime <= %s)
        ORDER BY event_datetime ASC
        LIMIT %s;
    """

    return run_query(
        query,
        [
            person_id,
            event_types,
            start_datetime,
            start_datetime,
            end_datetime,
            end_datetime,
            limit,
        ],
    )


def get_waveform_concepts():
    query = """
        SELECT concept_name
        FROM cdm.dashboard_waveform_concepts
        ORDER BY concept_name;
    """
    return run_query(query)


def get_waveform_data_multi(person_id, concept_names, limit=3000):
    query = """
        SELECT
            event_datetime,
            concept_name,
            AVG(value_numeric) AS value_numeric,
            MAX(NULLIF(unit_name, 'No matching concept')) AS unit_name,
            MAX(source_value) AS source_value
        FROM cdm.omop_longitudinal_events
        WHERE person_id = %s
          AND concept_name = ANY(%s)
          AND vocabulary_id = 'MIMIC-Wave-Derived'
          AND value_numeric IS NOT NULL
        GROUP BY
            event_datetime,
            concept_name
        ORDER BY
            event_datetime ASC,
            concept_name ASC
        LIMIT %s;
    """
    return run_query(query, [person_id, concept_names, limit])


def get_patient_medications(person_id, limit=500):
    query = """
        SELECT
            d.drug_exposure_start_datetime AS start_datetime,
            d.drug_exposure_end_datetime AS end_datetime,

            CASE
                WHEN d.drug_concept_id IS NOT NULL
                     AND d.drug_concept_id != 0
                     AND c_standard.concept_name IS NOT NULL
                     AND c_standard.concept_name != 'No matching concept'
                THEN c_standard.concept_name

                WHEN d.drug_source_value ~ '^[0-9]+$'
                THEN COALESCE(
                    c_ndc.concept_name,
                    CONCAT('Rx NDC: ', d.drug_source_value)
                )

                ELSE COALESCE(
                    NULLIF(d.drug_source_value, ''),
                    NULLIF(c_source.concept_name, 'No matching concept'),
                    'Unknown medication'
                )
            END AS medication_name,

            d.quantity,
            d.dose_unit_source_value AS unit,
            d.drug_source_value AS source_value

        FROM cdm.dashboard_patient_summary s
        JOIN cdm.drug_exposure d
            ON s.omop_person_id = d.person_id
        LEFT JOIN cdm.concept c_standard
            ON d.drug_concept_id = c_standard.concept_id
        LEFT JOIN cdm.concept c_source
            ON d.drug_source_concept_id = c_source.concept_id
        LEFT JOIN cdm.concept c_ndc
            ON c_ndc.concept_code = d.drug_source_value
           AND c_ndc.vocabulary_id IN ('NDC', 'RxNorm', 'RxNorm Extension')

        WHERE s.display_patient_id = %s
          AND s.has_omop_mapping = TRUE

        ORDER BY d.drug_exposure_start_datetime ASC
        LIMIT %s;
    """
    return run_query(query, [person_id, limit])


def get_patient_conditions(person_id, limit=500):
    query = """
        SELECT
            co.condition_start_datetime AS event_datetime,

            COALESCE(
                c_icd.concept_name,
                NULLIF(co.condition_source_value, ''),
                'Unknown condition'
            ) AS concept_name,

            co.condition_source_value AS source_value,
            COALESCE(c_icd.vocabulary_id, 'Unknown') AS vocabulary_id,
            c_icd.concept_code,
            c_icd.concept_id

        FROM cdm.dashboard_patient_summary s
        JOIN cdm.condition_occurrence co
            ON s.omop_person_id = co.person_id
        LEFT JOIN cdm.concept c_icd
            ON REPLACE(c_icd.concept_code, '.', '') = co.condition_source_value
           AND c_icd.vocabulary_id IN ('ICD9CM', 'ICD10CM')

        WHERE s.display_patient_id = %s
          AND s.has_omop_mapping = TRUE

        ORDER BY co.condition_start_datetime ASC
        LIMIT %s;
    """
    return run_query(query, [person_id, limit])


def get_patient_observations(person_id, limit=50):
    query = """
        SELECT
            COALESCE(o.observation_datetime, o.observation_date::timestamp) AS event_datetime,

            CASE
                WHEN o.value_as_string IS NOT NULL
                     AND o.value_as_string <> ''
                THEN o.value_as_string

                WHEN o.value_as_number IS NOT NULL
                THEN o.value_as_number::text

                WHEN o.observation_source_value IS NOT NULL
                     AND o.observation_source_value <> ''
                THEN o.observation_source_value

                WHEN c.concept_name IS NOT NULL
                     AND c.concept_name <> 'No matching concept'
                THEN c.concept_name

                ELSE 'Unknown observation'
            END AS observation_value,

            CASE
                WHEN c.concept_name IS NOT NULL
                     AND c.concept_name <> 'No matching concept'
                THEN c.concept_name
                ELSE NULL
            END AS observation_type,

            o.value_as_string,
            o.value_as_number,
            o.observation_source_value,
            c.concept_name AS mapped_concept_name,
            c.vocabulary_id

        FROM cdm.dashboard_patient_summary s
        JOIN cdm.observation o
            ON s.omop_person_id = o.person_id
        LEFT JOIN cdm.concept c
            ON o.observation_concept_id = c.concept_id

        WHERE s.display_patient_id = %s
          AND s.has_omop_mapping = TRUE
          AND (
              (c.concept_name IS NOT NULL AND c.concept_name <> 'No matching concept')
              OR (o.value_as_string IS NOT NULL AND o.value_as_string <> '')
              OR (o.value_as_number IS NOT NULL)
              OR (o.observation_source_value IS NOT NULL AND o.observation_source_value <> '')
          )

        ORDER BY COALESCE(o.observation_datetime, o.observation_date::timestamp) ASC
        LIMIT %s;
    """
    return run_query(query, [person_id, limit])


def get_patient_notes(person_id, limit=7, offset=0):
    query = """
        SELECT
            n.note_datetime,
            n.note_title,
            n.note_text,
            n.note_source_value,
            n.person_id AS note_person_id
        FROM cdm.note n
        WHERE n.person_id IN (
            SELECT omop_person_id
            FROM cdm.dashboard_patient_summary
            WHERE display_patient_id = %s
              AND omop_person_id IS NOT NULL

            UNION

            SELECT display_patient_id
            FROM cdm.dashboard_patient_summary
            WHERE display_patient_id = %s
        )
        ORDER BY n.note_datetime ASC
        LIMIT %s OFFSET %s;
    """
    return run_query(query, [person_id, person_id, limit, offset])