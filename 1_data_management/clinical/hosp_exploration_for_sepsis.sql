-- --- CONFIGURATION ---
.mode markdown
.header on

DROP TABLE IF EXISTS treated_admissions;
DROP TABLE IF EXISTS treated_d_icd_diagnoses;
DROP TABLE IF EXISTS treated_d_labitems;
DROP TABLE IF EXISTS treated_diagnoses_icd;
DROP TABLE IF EXISTS treated_emar;
DROP TABLE IF EXISTS treated_labevents;
DROP TABLE IF EXISTS treated_microbiologyevents;
DROP TABLE IF EXISTS treated_patients;
DROP TABLE IF EXISTS treated_prescriptions;
DROP TABLE IF EXISTS treated_procedures_icd;

-- 1. filter by tables relevance --
 CREATE OR REPLACE VIEW v_admissions AS SELECT * FROM '../data/hosp/admissions.csv.gz'; -- essential
 CREATE OR REPLACE VIEW v_diagnoses_icd AS SELECT * FROM '../data/hosp/diagnoses_icd.csv.gz'; -- essential
 -- CREATE OR REPLACE VIEW v_drgcodes AS SELECT * FROM '../data/hosp/drgcodes.csv.gz';
 -- CREATE OR REPLACE VIEW v_d_hcpcs AS SELECT * FROM '../data/hosp/d_hcpcs.csv.gz';
 CREATE OR REPLACE VIEW v_d_icd_diagnoses AS SELECT * FROM '../data/hosp/d_icd_diagnoses.csv.gz'; -- essential
 CREATE OR REPLACE VIEW v_d_icd_procedures AS SELECT * FROM '../data/hosp/d_icd_procedures.csv.gz'; -- essential
 CREATE OR REPLACE VIEW v_d_labitems AS SELECT * FROM '../data/hosp/d_labitems.csv.gz'; -- essential
 CREATE OR REPLACE VIEW v_emar AS SELECT * FROM '../data/hosp/emar.csv.gz'; -- essential
 -- CREATE OR REPLACE VIEW v_emar_detail AS SELECT * FROM '../data/hosp/emar_detail.csv.gz'; -- essential
 -- CREATE OR REPLACE VIEW v_hcpcsevents AS SELECT * FROM '../data/hosp/hcpcsevents.csv.gz';
 CREATE OR REPLACE VIEW v_labevents AS SELECT * FROM '../data/hosp/labevents.csv.gz'; -- essential
 CREATE OR REPLACE VIEW v_microbiologyevents AS SELECT * FROM '../data/hosp/microbiologyevents.csv.gz'; -- essential
 -- CREATE OR REPLACE VIEW v_omr AS SELECT * FROM '../data/hosp/omr.csv.gz';
 CREATE OR REPLACE VIEW v_patients AS SELECT * FROM '../data/hosp/patients.csv.gz'; -- essential
 -- CREATE OR REPLACE VIEW v_pharmacy AS SELECT * FROM '../data/hosp/pharmacy.csv.gz';
 -- CREATE OR REPLACE VIEW v_poe AS SELECT * FROM '../data/hosp/poe.csv.gz';
 -- CREATE OR REPLACE VIEW v_poe_detail AS SELECT * FROM '../data/hosp/poe_detail.csv.gz';
 CREATE OR REPLACE VIEW v_prescriptions AS SELECT * FROM '../data/hosp/prescriptions.csv.gz'; -- essential
 CREATE OR REPLACE VIEW v_procedures_icd AS SELECT * FROM '../data/hosp/procedures_icd.csv.gz'; -- essential
 -- CREATE OR REPLACE VIEW v_provider AS SELECT * FROM '../data/hosp/provider.csv.gz';
 -- CREATE OR REPLACE VIEW v_services AS SELECT * FROM '../data/hosp/services.csv.gz';
 -- CREATE OR REPLACE VIEW v_transfers AS SELECT * FROM '../data/hosp/transfers.csv.gz';

 -- 2. Manual filter by list of all columns of all views --
 SELECT table_name, column_name, data_type 
 FROM information_schema.columns 
 WHERE table_name LIKE 'v_%'
 ORDER BY table_name;


CREATE TABLE treated_admissions AS 
 SELECT 
    subject_id, 
    hadm_id, 
    admittime, 
    dischtime, 
    deathtime, 
    hospital_expire_flag, 
    admission_type, 
    race
FROM v_admissions;

CREATE TABLE treated_d_icd_diagnoses AS 
 SELECT 
    *
FROM v_d_icd_diagnoses;

CREATE TABLE treated_d_icd_procedures AS 
 SELECT 
    *
FROM v_d_icd_procedures;

CREATE TABLE treated_d_labitems AS 
 SELECT 
    *
FROM v_d_labitems;

CREATE TABLE treated_diagnoses_icd AS 
 SELECT 
    *
FROM v_diagnoses_icd;

CREATE TABLE treated_emar AS 
SELECT 
    subject_id, 
    hadm_id, 
    charttime, 
    medication, 
    event_txt, 
    scheduletime
FROM v_emar
WHERE event_txt = 'Administered'; -- remove 'Refused', 'Held', and 'Cancelled' rows

CREATE TABLE treated_labevents AS 
SELECT 
    subject_id, 
    hadm_id, 
    itemid, 
    charttime, 
    valuenum, 
    valueuom, 
    flag
FROM v_labevents
WHERE valuenum IS NOT NULL; -- discard data without unit of measurement

CREATE TABLE treated_microbiologyevents AS 
SELECT 
    subject_id, 
    hadm_id, 
    COALESCE(charttime, chartdate) as culture_time, -- if charttime is empty, use the date and 00:00 for time reference (reduce null data)
    spec_type_desc, 
    test_name, 
    org_name, 
    ab_name, 
    interpretation
FROM v_microbiologyevents;

CREATE TABLE treated_patients AS 
SELECT 
    subject_id, 
    gender, 
    anchor_age, 
    dod
FROM v_patients;

CREATE TABLE treated_prescriptions AS 
SELECT 
    subject_id, 
    hadm_id, 
    drug, 
    starttime, 
    stoptime, 
    dose_val_rx, 
    dose_unit_rx, 
    route, 
    doses_per_24_hrs
FROM v_prescriptions
WHERE drug_type = 'MAIN'; -- remove rows of 'Base' fluids and 'Additives'
 
CREATE TABLE treated_procedures_icd AS 
SELECT 
    subject_id, 
    hadm_id, 
    chartdate, 
    icd_code, 
    icd_version
FROM v_procedures_icd;

 -- 3. filter by null count ('ok' means no column was erased due to exccess of missing data)--
SUMMARIZE treated_admissions; --ok
SUMMARIZE treated_d_icd_diagnoses; --ok
SUMMARIZE treated_d_icd_procedures; --ok
SUMMARIZE treated_d_labitems; --ok
SUMMARIZE treated_patients; --ok
SUMMARIZE treated_labevents; --ok
SUMMARIZE treated_emar; --ok
SUMMARIZE treated_prescriptions; --ok
SUMMARIZE treated_microbiologyevents; --ok
SUMMARIZE treated_diagnoses_icd; --ok
SUMMARIZE treated_procedures_icd; --ok
