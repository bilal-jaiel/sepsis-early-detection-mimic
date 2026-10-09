-- --- CONFIGURATION ---
.mode markdown
.header on

DROP TABLE IF EXISTS treated_admissions; --1
DROP TABLE IF EXISTS treated_diagnoses_icd; --2
DROP TABLE IF EXISTS treated_drgcodes; --3
DROP TABLE IF EXISTS treated_d_hcpcs; --4
DROP TABLE IF EXISTS treated_d_icd_diagnoses; --5
DROP TABLE IF EXISTS treated_d_icd_procedures; --6
DROP TABLE IF EXISTS treated_d_labitems; --7
DROP TABLE IF EXISTS treated_emar; --8
DROP TABLE IF EXISTS treated_hcpcsevents; --10
DROP TABLE IF EXISTS treated_labevents; --11
DROP TABLE IF EXISTS treated_microbiologyevents; --12
DROP TABLE IF EXISTS treated_omr; --13
DROP TABLE IF EXISTS treated_patients; --14
DROP TABLE IF EXISTS treated_pharmacy; --15
DROP TABLE IF EXISTS treated_poe; --16
DROP TABLE IF EXISTS treated_poe_detail; --17
DROP TABLE IF EXISTS treated_prescriptions; --18
DROP TABLE IF EXISTS treated_procedures_icd; --19
DROP TABLE IF EXISTS treated_provider; --20
DROP TABLE IF EXISTS treated_services; --21
DROP TABLE IF EXISTS treated_transfers; --22


-- 1. filter by tables relevance --
 CREATE OR REPLACE VIEW v_admissions AS SELECT * FROM '../data/hosp/admissions.csv.gz'; 
 CREATE OR REPLACE VIEW v_diagnoses_icd AS SELECT * FROM '../data/hosp/diagnoses_icd.csv.gz'; 
 CREATE OR REPLACE VIEW v_drgcodes AS SELECT * FROM '../data/hosp/drgcodes.csv.gz';
 CREATE OR REPLACE VIEW v_d_hcpcs AS SELECT * FROM '../data/hosp/d_hcpcs.csv.gz';
 CREATE OR REPLACE VIEW v_d_icd_diagnoses AS SELECT * FROM '../data/hosp/d_icd_diagnoses.csv.gz'; 
 CREATE OR REPLACE VIEW v_d_icd_procedures AS SELECT * FROM '../data/hosp/d_icd_procedures.csv.gz'; 
 CREATE OR REPLACE VIEW v_d_labitems AS SELECT * FROM '../data/hosp/d_labitems.csv.gz'; 
 CREATE OR REPLACE VIEW v_emar AS SELECT * FROM '../data/hosp/emar.csv.gz'; 
 --CREATE OR REPLACE VIEW v_emar_detail AS SELECT * FROM '../data/hosp/emar_detail.csv.gz'; -- too many null values
 CREATE OR REPLACE VIEW v_hcpcsevents AS SELECT * FROM '../data/hosp/hcpcsevents.csv.gz';
 CREATE OR REPLACE VIEW v_labevents AS SELECT * FROM '../data/hosp/labevents.csv.gz'; 
 CREATE OR REPLACE VIEW v_microbiologyevents AS SELECT * FROM '../data/hosp/microbiologyevents.csv.gz'; 
 CREATE OR REPLACE VIEW v_omr AS SELECT * FROM '../data/hosp/omr.csv.gz';
 CREATE OR REPLACE VIEW v_patients AS SELECT * FROM '../data/hosp/patients.csv.gz'; 
 CREATE OR REPLACE VIEW v_pharmacy AS 
 SELECT * FROM read_csv('../data/hosp/pharmacy.csv.gz', sample_size = -1);
 CREATE OR REPLACE VIEW v_poe AS SELECT * FROM '../data/hosp/poe.csv.gz';
 CREATE OR REPLACE VIEW v_poe_detail AS SELECT * FROM '../data/hosp/poe_detail.csv.gz';
 CREATE OR REPLACE VIEW v_prescriptions AS SELECT * FROM '../data/hosp/prescriptions.csv.gz'; 
 CREATE OR REPLACE VIEW v_procedures_icd AS SELECT * FROM '../data/hosp/procedures_icd.csv.gz'; 
 CREATE OR REPLACE VIEW v_provider AS SELECT * FROM '../data/hosp/provider.csv.gz';
 CREATE OR REPLACE VIEW v_services AS SELECT * FROM '../data/hosp/services.csv.gz';
 CREATE OR REPLACE VIEW v_transfers AS SELECT * FROM '../data/hosp/transfers.csv.gz';

-- filter irrelevant or empty columns --

/*
The workflow for the performance of data pruning was based on the following criteria:
1) irrelevant variables
2) redundant variables
3) too numerous and uninformative missing data
4) low variance
*/

-- 1
-- columns pruned:  edregtime, edouttime, language, marital_status, insurance, 
CREATE TABLE treated_admissions AS 
SELECT 
    subject_id, hadm_id, admittime, dischtime, deathtime, admission_type, 
    admit_provider_id, admission_location, discharge_location, insurance, 
    race, hospital_expire_flag 
FROM v_admissions;

-- 2 
-- columns unchanged
CREATE TABLE treated_diagnoses_icd AS 
SELECT subject_id, hadm_id, seq_num, icd_code, icd_version 
FROM v_diagnoses_icd;

-- 3 
-- columns unchanged
CREATE TABLE treated_drgcodes AS 
SELECT subject_id, hadm_id, drg_type, drg_code, description, drg_severity, drg_mortality 
FROM v_drgcodes;

-- 4
-- pruned columns: long_description (92.38% null)
CREATE TABLE treated_d_hcpcs AS 
SELECT code, category, short_description 
FROM v_d_hcpcs;

-- 5 
-- columns unchanged
CREATE TABLE treated_d_icd_diagnoses AS 
SELECT icd_code, icd_version, long_title 
FROM v_d_icd_diagnoses;

-- 6 
-- columns unchanged
CREATE TABLE treated_d_icd_procedures AS 
SELECT icd_code, icd_version, long_title 
FROM v_d_icd_procedures;

-- 7 
-- columns unchanged
CREATE TABLE treated_d_labitems AS 
SELECT itemid, label, fluid, category 
FROM v_d_labitems;

-- 8
-- pruned columns: storetime
CREATE TABLE treated_emar AS 
SELECT 
    subject_id, hadm_id, emar_id, emar_seq, poe_id, pharmacy_id, 
    enter_provider_id, charttime, medication, event_txt, scheduletime 
FROM v_emar
WHERE event_txt = 'Administered'; -- remove 'Refused', 'Held', and 'Cancelled' rows

-- 10 
-- columns unchanged
CREATE TABLE treated_hcpcsevents AS 
SELECT subject_id, hadm_id, chartdate, hcpcs_cd, seq_num, short_description 
FROM v_hcpcsevents;

-- 11 
-- pruned columns: storetime, valuenum (contained inside 'value')
CREATE TABLE treated_labevents AS 
SELECT 
    labevent_id, subject_id, hadm_id, specimen_id, itemid, order_provider_id, 
    charttime, value, valueuom, ref_range_lower, 
    ref_range_upper, flag, priority, comments 
FROM v_labevents;

-- 12 
-- pruned columns: storetime, storedate, quantity (100% null), 
CREATE TABLE treated_microbiologyevents AS 
SELECT 
    microevent_id, subject_id, hadm_id, micro_specimen_id, order_provider_id, 
    COALESCE(charttime, chartdate) as culture_time, -- if charttime is empty, use the date and 00:00 for time reference (reduce null data)
    spec_itemid, spec_type_desc, test_seq, test_itemid, test_name, org_itemid, org_name, isolate_num, ab_itemid, ab_name, dilution_text, dilution_comparison, 
    dilution_value, interpretation, comments 
FROM v_microbiologyevents;

-- 13 
-- columns unchanged
CREATE TABLE treated_omr AS 
SELECT subject_id, chartdate, seq_num, result_name, result_value 
FROM v_omr;

-- 14 
-- pruned columns: anchor_year_group
CREATE TABLE treated_patients AS 
SELECT subject_id, gender, anchor_age, anchor_year, dod 
FROM v_patients;

-- 15
-- pruned columns: entertime, verifiedtime, fill_quantity (99.88% null), expirationdate (99.88% null), one_hr_max(99.65%)
CREATE TABLE treated_pharmacy AS 
SELECT 
    subject_id, hadm_id, pharmacy_id, poe_id, starttime, stoptime, medication, 
    proc_type, status, route, frequency, disp_sched, 
    infusion_type, sliding_scale, lockout_interval, basal_rate, 
    doses_per_24_hrs, duration, duration_interval, expiration_value, 
    expiration_unit, dispensation 
FROM v_pharmacy;

-- 16
-- pruned columns: poe_seq (highly erratic), transaction_type (often redundant with order_status and discontinue IDs)
CREATE TABLE treated_poe AS 
SELECT 
    poe_id, subject_id, hadm_id, ordertime, order_type, order_subtype, discontinue_of_poe_id, discontinued_by_poe_id, 
    order_provider_id, order_status 
FROM v_poe;

-- 17
-- columns unchanged
CREATE TABLE treated_poe_detail AS 
SELECT poe_id, poe_seq, subject_id, field_name, field_value 
FROM v_poe_detail;

-- 18
-- pruned columns: form_rx (99.85% null)
CREATE TABLE treated_prescriptions AS 
SELECT 
    subject_id, hadm_id, pharmacy_id, poe_id, poe_seq, order_provider_id, 
    starttime, stoptime, drug_type, drug, formulary_drug_cd, gsn, ndc, 
    prod_strength, dose_val_rx, dose_unit_rx, form_val_disp, 
    form_unit_disp, doses_per_24_hrs, route 
FROM v_prescriptions
WHERE drug_type = 'MAIN'; -- remove rows of 'Base' fluids and 'Additives'

-- 19
-- columns unchanged
CREATE TABLE treated_procedures_icd AS 
SELECT subject_id, hadm_id, seq_num, chartdate, icd_code, icd_version 
FROM v_procedures_icd;

-- 20
-- columns unchanged
CREATE TABLE treated_provider AS 
SELECT provider_id 
FROM v_provider;

-- 21
-- columns unchanged
CREATE TABLE treated_services AS 
SELECT subject_id, hadm_id, transfertime, prev_service, curr_service 
FROM v_services;

-- 22
-- columns unchanged
CREATE TABLE treated_transfers AS 
SELECT subject_id, hadm_id, transfer_id, eventtype, careunit, intime, outtime 
FROM v_transfers;


SUMMARIZE treated_admissions; --1
SUMMARIZE treated_diagnoses_icd; --2 ok unchanged
SUMMARIZE treated_drgcodes; --3 unchanged
SUMMARIZE treated_d_hcpcs; --4 
SUMMARIZE treated_d_icd_diagnoses; --5 ok unchanged
SUMMARIZE treated_d_icd_procedures; --6 ok unchanged
SUMMARIZE treated_d_labitems; --7 unchanged
SUMMARIZE treated_emar; --8
-- SUMMARIZE treated_emar_detail; --9 almost empty table
SUMMARIZE treated_hcpcsevents; --10 ok
SUMMARIZE treated_labevents; --11
SUMMARIZE treated_microbiologyevents; --12
SUMMARIZE treated_omr; --13 ok
SUMMARIZE treated_patients; --14 ok
SUMMARIZE treated_pharmacy; --15
SUMMARIZE treated_poe; --16
SUMMARIZE treated_poe_detail; --17 ok
SUMMARIZE treated_prescriptions; --18
SUMMARIZE treated_procedures_icd; --19 ok
SUMMARIZE treated_provider; --20 ok
SUMMARIZE treated_services; --21
SUMMARIZE treated_transfers; --22
