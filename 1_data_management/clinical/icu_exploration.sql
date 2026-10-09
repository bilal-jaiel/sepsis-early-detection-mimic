-- --- CONFIGURATION AFFICHAGE ---
.mode markdown
.header on

-- -- --- CRÉATION DES VUES POUR TOUTES LES TABLES HOSP ---
-- CREATE OR REPLACE VIEW v_admissions AS SELECT * FROM '../mimic-iv-3.1/hosp/admissions.csv.gz';
-- CREATE OR REPLACE VIEW v_diagnoses_icd AS SELECT * FROM '../mimic-iv-3.1/hosp/diagnoses_icd.csv.gz';
-- CREATE OR REPLACE VIEW v_drgcodes AS SELECT * FROM '../mimic-iv-3.1/hosp/drgcodes.csv.gz';
-- CREATE OR REPLACE VIEW v_d_hcpcs AS SELECT * FROM '../mimic-iv-3.1/hosp/d_hcpcs.csv.gz';
-- CREATE OR REPLACE VIEW v_d_icd_diagnoses AS SELECT * FROM '../mimic-iv-3.1/hosp/d_icd_diagnoses.csv.gz';
-- CREATE OR REPLACE VIEW v_d_icd_procedures AS SELECT * FROM '../mimic-iv-3.1/hosp/d_icd_procedures.csv.gz';
-- CREATE OR REPLACE VIEW v_d_labitems AS SELECT * FROM '../mimic-iv-3.1/hosp/d_labitems.csv.gz';
-- CREATE OR REPLACE VIEW v_emar AS SELECT * FROM '../mimic-iv-3.1/hosp/emar.csv.gz';
-- CREATE OR REPLACE VIEW v_emar_detail AS SELECT * FROM '../mimic-iv-3.1/hosp/emar_detail.csv.gz';
-- CREATE OR REPLACE VIEW v_hcpcsevents AS SELECT * FROM '../mimic-iv-3.1/hosp/hcpcsevents.csv.gz';
-- CREATE OR REPLACE VIEW v_labevents AS SELECT * FROM '../mimic-iv-3.1/hosp/labevents.csv.gz';
-- CREATE OR REPLACE VIEW v_microbiologyevents AS SELECT * FROM '../mimic-iv-3.1/hosp/microbiologyevents.csv.gz';
-- CREATE OR REPLACE VIEW v_omr AS SELECT * FROM '../mimic-iv-3.1/hosp/omr.csv.gz';
-- CREATE OR REPLACE VIEW v_patients AS SELECT * FROM '../mimic-iv-3.1/hosp/patients.csv.gz';
-- CREATE OR REPLACE VIEW v_pharmacy AS SELECT * FROM '../mimic-iv-3.1/hosp/pharmacy.csv.gz';
-- CREATE OR REPLACE VIEW v_poe AS SELECT * FROM '../mimic-iv-3.1/hosp/poe.csv.gz';
-- CREATE OR REPLACE VIEW v_poe_detail AS SELECT * FROM '../mimic-iv-3.1/hosp/poe_detail.csv.gz';
-- CREATE OR REPLACE VIEW v_prescriptions AS SELECT * FROM '../mimic-iv-3.1/hosp/prescriptions.csv.gz';
-- CREATE OR REPLACE VIEW v_procedures_icd AS SELECT * FROM '../mimic-iv-3.1/hosp/procedures_icd.csv.gz';
-- CREATE OR REPLACE VIEW v_provider AS SELECT * FROM '../mimic-iv-3.1/hosp/provider.csv.gz';
-- CREATE OR REPLACE VIEW v_services AS SELECT * FROM '../mimic-iv-3.1/hosp/services.csv.gz';
-- CREATE OR REPLACE VIEW v_transfers AS SELECT * FROM '../mimic-iv-3.1/hosp/transfers.csv.gz';

-- -- Liste toutes les colonnes de toutes les vues
-- SELECT table_name, column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name LIKE 'v_%'
-- ORDER BY table_name;





-- ICU
CREATE OR REPLACE VIEW v_caregiver AS SELECT * FROM '../mimic-iv-3.1/icu/caregiver.csv.gz';
CREATE OR REPLACE VIEW v_chartevents AS SELECT * FROM '../mimic-iv-3.1/icu/chartevents.csv.gz';
CREATE OR REPLACE VIEW v_d_items AS SELECT * FROM '../mimic-iv-3.1/icu/d_items.csv.gz';
CREATE OR REPLACE VIEW v_datetimeevents AS SELECT * FROM '../mimic-iv-3.1/icu/datetimeevents.csv.gz';
CREATE OR REPLACE VIEW v_icustays AS SELECT * FROM '../mimic-iv-3.1/icu/icustays.csv.gz';
CREATE OR REPLACE VIEW v_ingredientevents AS SELECT * FROM '../mimic-iv-3.1/icu/ingredientevents.csv.gz';
CREATE OR REPLACE VIEW v_inputevents AS SELECT * FROM '../mimic-iv-3.1/icu/inputevents.csv.gz';
CREATE OR REPLACE VIEW v_outputevents AS SELECT * FROM '../mimic-iv-3.1/icu/outputevents.csv.gz';
CREATE OR REPLACE VIEW v_procedureevents AS SELECT * FROM '../mimic-iv-3.1/icu/procedureevents.csv.gz';


-- Liste toutes les colonnes pour les tables ICU chargées
SELECT 
    table_name, 
    column_name, 
    data_type
FROM information_schema.columns 
WHERE table_name IN (
    'v_caregiver', 
    'v_chartevents', 
    'v_d_items', 
    'v_datetimeevents', 
    'v_icustays', 
    'v_ingredientevents', 
    'v_inputevents', 
    'v_outputevents', 
    'v_procedureevents'
)
ORDER BY table_name, ordinal_position;

--Treaeted tables:--
-- treated_icustays
CREATE OR REPLACE TABLE treated_icustays AS 
SELECT stay_id, first_careunit, intime, outtime, los 
FROM v_icustays;

-- treated_chartevents
CREATE OR REPLACE TABLE treated_chartevents AS 
SELECT stay_id, charttime, itemid, valuenum, valueuom 
FROM v_chartevents ;

-- treated_d_items
CREATE OR REPLACE TABLE treated_d_items AS 
SELECT itemid, label, abbreviation, lownormalvalue, highnormalvalue 
FROM v_d_items;

-- treated_inputevents
CREATE OR REPLACE TABLE treated_inputevents AS 
SELECT stay_id, starttime, endtime, itemid, amount, rate, amountuom, rateuom, patientweight 
FROM v_inputevents;

-- treated_outputevents
CREATE OR REPLACE TABLE treated_outputevents AS 
SELECT stay_id, charttime, itemid, value, valueuom 
FROM v_outputevents;

-- treated_procedureevents
CREATE OR REPLACE TABLE treated_procedureevents AS 
SELECT stay_id, starttime, endtime, itemid, value, valueuom 
FROM v_procedureevents;

-- treated_ingredientevents
CREATE OR REPLACE TABLE treated_ingredientevents AS 
SELECT stay_id, starttime, endtime, itemid, amount, rate, amountuom, rateuom 
FROM v_ingredientevents;

-- treated_datetimeevents
CREATE OR REPLACE TABLE treated_datetimeevents AS 
SELECT stay_id, itemid, charttime, value 
FROM v_datetimeevents;

-- treated_caregiver (Empty)


-- Show % of missing values for each column in treated_chartevents--
SELECT 'treated_icustays' as tbl, count(*) as total, 
       round(count(stay_id)*100.0/count(*), 2) as fill_rate_pct FROM treated_icustays
UNION ALL
SELECT 'treated_chartevents', count(*), 
       round(count(valuenum)*100.0/count(*), 2) FROM treated_chartevents
UNION ALL
SELECT 'treated_d_items', count(*), 
       round(count(label)*100.0/count(*), 2) FROM treated_d_items
UNION ALL
SELECT 'treated_inputevents', count(*), 
       round(count(rate)*100.0/count(*), 2) FROM treated_inputevents
UNION ALL
SELECT 'treated_outputevents', count(*), 
       round(count(value)*100.0/count(*), 2) FROM treated_outputevents
UNION ALL
SELECT 'treated_procedureevents', count(*), 
       round(count(value)*100.0/count(*), 2) FROM treated_procedureevents
UNION ALL
SELECT 'treated_ingredientevents', count(*), 
       round(count(amount)*100.0/count(*), 2) FROM treated_ingredientevents
UNION ALL
SELECT 'treated_datetimeevents', count(*), 
       round(count(value)*100.0/count(*), 2) FROM treated_datetimeevents;








--After the presentation professor told we deleted too many variables, at this point we dont need to understand the variables, we just need to look at their variance and missing values et deletes the most flagrant ones.

--Showing all variables--
SELECT 
    table_name, 
    column_name, 
    data_type
FROM information_schema.columns 
WHERE table_name IN (
    'v_caregiver', 
    'v_chartevents', 
    'v_d_items', 
    'v_datetimeevents', 
    'v_icustays', 
    'v_ingredientevents', 
    'v_inputevents', 
    'v_outputevents', 
    'v_procedureevents'
)
ORDER BY table_name, ordinal_position;

--Showing % of missing values for each column --
--we use now python...-