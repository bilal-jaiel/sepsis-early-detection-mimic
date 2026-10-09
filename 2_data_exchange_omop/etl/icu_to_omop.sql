---Creations of dictionnaries---
-- 1. Table VOCABULARY
CREATE TABLE vocabulary (
  vocabulary_id         varchar(50)   NOT NULL,
  vocabulary_name       varchar(500)  NOT NULL,
  vocabulary_reference  varchar(500)  NULL,
  vocabulary_version    varchar(500)  NULL,
  vocabulary_concept_id integer       NOT NULL
);

-- 2. Table CONCEPT (avec varchar(2000) pour les noms longs)
CREATE TABLE concept (
  concept_id          integer       NOT NULL,
  concept_name        varchar(2000) NOT NULL,
  domain_id           varchar(50)   NOT NULL,
  vocabulary_id       varchar(50)   NOT NULL,
  concept_class_id    varchar(50)   NOT NULL,
  standard_concept    varchar(1)    NULL,
  concept_code        varchar(255)  NOT NULL,
  valid_start_date    date          NOT NULL,
  valid_end_date      date          NOT NULL,
  invalid_reason      varchar(1)    NULL
);

-- 3. Table CONCEPT_RELATIONSHIP
CREATE TABLE concept_relationship (
  concept_id_1      integer     NOT NULL,
  concept_id_2      integer     NOT NULL,
  relationship_id   varchar(50) NOT NULL,
  valid_start_date  date        NOT NULL,
  valid_end_date    date        NOT NULL,
  invalid_reason    varchar(1)  NULL
);





---Import icu stays:---
CREATE TABLE icustays (
    subject_id integer,
    hadm_id integer,
    stay_id integer,
    first_careunit text,
    last_careunit text,
    intime timestamp,
    outtime timestamp,
    los double precision
);

Chartevents
CREATE TABLE chartevents (
    subject_id integer,
    hadm_id integer,
    stay_id integer,
    caregiver_id integer,
    charttime timestamp,
    itemid integer,
    value text, 
    valuenum double precision,
    warning integer
);

d_items
CREATE TABLE d_items (
    itemid integer,
    label text,
    abbreviation text,
    linksto text,
    category text,
    param_type text
);

datetimeevents
CREATE TABLE datetimeevents (
    subject_id integer,
    hadm_id integer,
    stay_id integer,
    caregiver_id integer,
    charttime timestamp,
    itemid integer,
    value timestamp,
    valueuom text,
    warning integer
);

CREATE TABLE icustays (
    subject_id integer,
    hadm_id integer,
    stay_id integer,
    first_careunit text,
    last_careunit text,
    intime timestamp,
    outtime timestamp,
    los double precision
);

CREATE TABLE ingredientevents (
    subject_id integer,
    hadm_id integer,
    stay_id integer,
    caregiver_id integer,
    starttime timestamp,
    endtime timestamp,
    itemid integer,
    amount double precision,
    amountuom text,
    rate double precision,
    rateuom text,
    orderid integer,
    linkorderid integer,
    statusdescription text,
    originalrate double precision
);

CREATE TABLE inputevents (
    subject_id integer,
    hadm_id integer,
    stay_id integer,
    caregiver_id integer,
    starttime timestamp,
    endtime timestamp,
    itemid integer,
    amount double precision,
    amountuom text,
    rate double precision,
    rateuom text,
    orderid integer,
    linkorderid integer,
    ordercategoryname text,
    secondaryordercategoryname text,
    ordercomponenttypedescription text,
    ordercategorydescription text,
    patientweight double precision,
    totalamount double precision,
    totalamountuom text,
    isopenbag integer,
    statusdescription text,
    originalamount double precision,
    originalrate double precision
);

CREATE TABLE outputevents (
    subject_id integer,
    hadm_id integer,
    stay_id integer,
    caregiver_id integer,
    charttime timestamp,
    itemid integer,
    value double precision,
    valueuom text
);

CREATE TABLE procedureevents (
    subject_id integer,
    hadm_id integer,
    stay_id integer,
    caregiver_id integer,
    starttime timestamp,
    endtime timestamp,
    itemid integer,
    value double precision,
    valueuom text,
    orderid integer,
    linkorderid integer,
    ordercategoryname text,
    ordercategorydescription text,
    patientweight double precision,
    isopenbag integer,
    continueinnextdept integer,
    statusdescription text,
    originalamount double precision,
    originalrate double precision
);




---- CONTRUCTION OF NEW TABLES ----

-- 1. Table PERSON
CREATE TABLE person (
    person_id integer,
    gender_concept_id integer,
    year_of_birth integer,
    month_of_birth integer,
    day_of_birth integer,
    birth_datetime timestamp,
    race_concept_id integer,
    ethnicity_concept_id integer,
    location_id integer,
    care_site_id integer,
    person_source_value text,
    gender_source_value text,
    gender_source_concept_id integer,
    race_source_value text,
    race_source_concept_id integer,
    ethnicity_source_value text,
    ethnicity_source_concept_id integer
);


INSERT INTO person (
    person_id,
    gender_concept_id,
    year_of_birth,
    month_of_birth,
    day_of_birth,
    birth_datetime,
    race_concept_id,
    ethnicity_concept_id,
    location_id,
    care_site_id,
    person_source_value,
    gender_source_value,
    gender_source_concept_id,
    race_source_value,
    race_source_concept_id,
    ethnicity_source_value,
    ethnicity_source_concept_id
)
SELECT 
    icu.subject_id AS person_id,
    -- Mapping Athena for gender(Standard Concept for 'Unknown')
    (SELECT concept_id FROM concept WHERE concept_id = 0) AS gender_concept_id, 
    -- default values for birth date (since we don't have this information in the source data)
    2000 AS year_of_birth, 
    1 AS month_of_birth,
    1 AS day_of_birth,
    NULL AS birth_datetime,
    (SELECT concept_id FROM concept WHERE concept_id = 0) AS race_concept_id,
    (SELECT concept_id FROM concept WHERE concept_id = 0) AS ethnicity_concept_id,
    NULL AS location_id,
    NULL AS care_site_id,
    icu.subject_id::text AS person_source_value,
    'Unknown' AS gender_source_value,
    0 AS gender_source_concept_id,
    'Unknown' AS race_source_value,
    0 AS race_source_concept_id,
    'Unknown' AS ethnicity_source_value,
    0 AS ethnicity_source_concept_id
FROM icustays icu
GROUP BY icu.subject_id;


-- 2. Table VISIT_OCCURRENCE
CREATE TABLE visit_occurrence (
    visit_occurrence_id           integer,
    person_id                     integer,
    visit_concept_id              integer,
    visit_start_date              date,
    visit_start_datetime          timestamp,
    visit_end_date                date,
    visit_end_datetime            timestamp,
    visit_type_concept_id         integer,
    provider_id                   integer,
    care_site_id                  integer,
    visit_source_value            text,
    visit_source_concept_id       integer,
    admitting_source_concept_id   integer,
    admitting_source_value        text,
    discharge_to_concept_id       integer,
    discharge_to_source_value     text,
    preceding_visit_occurrence_id integer
);

INSERT INTO visit_occurrence (
    visit_occurrence_id,
    person_id,
    visit_concept_id,
    visit_start_date,
    visit_start_datetime,
    visit_end_date,
    visit_end_datetime,
    visit_type_concept_id,
    provider_id,
    care_site_id,
    visit_source_value,
    visit_source_concept_id,
    admitting_source_concept_id,
    admitting_source_value,
    discharge_to_concept_id,
    discharge_to_source_value,
    preceding_visit_occurrence_id
)
SELECT 
    icu.stay_id AS visit_occurrence_id,
    icu.subject_id AS person_id,
    
    -- ATHENA : Mapping du type de visite (Inpatient/ICU)
    -- On cherche le concept standard 'Inpatient Visit'
    (SELECT concept_id FROM concept WHERE concept_code = 'IP' AND vocabulary_id = 'Visit' LIMIT 1) AS visit_concept_id,
    
    -- DATES : Transformation des timestamps en date et datetime
    CAST(icu.intime AS DATE) AS visit_start_date,
    icu.intime AS visit_start_datetime,
    CAST(icu.outtime AS DATE) AS visit_end_date,
    icu.outtime AS visit_end_datetime,
    
    -- ATHENA : Origine de la donnée (EHR administrative record)
    (SELECT concept_id FROM concept WHERE concept_code = 'EHR' AND vocabulary_id = 'Visit Type' LIMIT 1) AS visit_type_concept_id,
    
    NULL AS provider_id,
    NULL AS care_site_id,
    
    -- SOURCE VALUES : On garde les IDs originaux de MIMIC
    icu.hadm_id::text AS visit_source_value,
    0 AS visit_source_concept_id,
    0 AS admitting_source_concept_id,
    NULL AS admitting_source_value,
    0 AS discharge_to_concept_id,
    NULL AS discharge_to_source_value,
    NULL AS preceding_visit_occurrence_id

FROM icustays icu;

---Measurement
CREATE TABLE measurement (
    measurement_id                SERIAL, -- Génère un ID unique automatiquement
    person_id                     integer,
    measurement_concept_id        integer,
    measurement_date              date,
    measurement_datetime          timestamp,
    measurement_time              text,
    measurement_type_concept_id   integer,
    operator_concept_id           integer,
    value_as_number               numeric,
    value_as_concept_id           integer,
    unit_concept_id               integer,
    range_low                     numeric,
    range_high                    numeric,
    provider_id                   integer,
    visit_occurrence_id           integer,
    visit_detail_id               integer,
    measurement_source_value      text,
    measurement_source_concept_id integer,
    unit_source_value             text,
    unit_source_concept_id        integer,
    value_source_value            text,
    measurement_event_id          integer,
    meas_event_field_concept_id   integer
);

INSERT INTO measurement (
    person_id,
    measurement_concept_id,
    measurement_date,
    measurement_datetime,
    measurement_type_concept_id,
    value_as_number,
    visit_occurrence_id,
    measurement_source_value,
    unit_source_value
)
SELECT 
    c.subject_id,
    -- ATHENA : On tente de mapper l'itemid MIMIC vers un concept standard
    -- Si pas trouvé, on met 0
    COALESCE(
        (SELECT concept_id FROM concept 
         WHERE concept_code = c.itemid::text 
         AND vocabulary_id = 'MIMIC d_items' LIMIT 1), 
        0
    ),
    CAST(c.charttime AS DATE),
    c.charttime,
    -- ATHENA : Concept pour 'Lab result' ou 'EHR'
    44818701, 
    c.valuenum,
    c.stay_id,
    c.itemid::text,
    NULL -- L'unité pourra être ajoutée via une jointure d_items plus tard
FROM chartevents c
LIMIT 100000; -- On limite pour un premier test car chartevents est énorme



---Observation
CREATE TABLE observation (
    observation_id                SERIAL,
    person_id                     integer,
    observation_concept_id        integer,
    observation_date              date,
    observation_datetime          timestamp,
    observation_type_concept_id   integer,
    value_as_number               numeric,
    value_as_string               text,
    value_as_concept_id           integer,
    qualifier_concept_id          integer,
    unit_concept_id               integer,
    provider_id                   integer,
    visit_occurrence_id           integer,
    visit_detail_id               integer,
    observation_source_value      text,
    observation_source_concept_id integer,
    unit_source_value             text,
    qualifier_source_value        text,
    value_source_value            text,
    observation_event_id          integer,
    obs_event_field_concept_id    integer
);

INSERT INTO observation (
    person_id,
    observation_concept_id,
    observation_date,
    observation_datetime,
    observation_type_concept_id,
    value_as_string,
    visit_occurrence_id,
    observation_source_value
)
SELECT 
    d.subject_id,
    -- ATHENA : Mapping dynamique de l'itemid
    COALESCE(
        (SELECT concept_id FROM concept 
         WHERE concept_code = d.itemid::text 
         AND vocabulary_id = 'MIMIC d_items' LIMIT 1), 
        0
    ),
    CAST(d.charttime AS DATE),
    d.charttime,
    32817, -- Concept Athena pour 'EHR'
    d.value::text,
    v.visit_occurrence_id, -- On lie à la visite via hadm_id
    d.itemid::text
FROM datetimeevents d
LEFT JOIN visit_occurrence v ON d.hadm_id::text = v.visit_source_value;

INSERT INTO observation (
    person_id,
    observation_concept_id,
    observation_date,
    observation_datetime,
    observation_type_concept_id,
    value_as_number,
    unit_source_value,
    visit_occurrence_id,
    observation_source_value
)
SELECT 
    o.subject_id,
    -- ATHENA : Mapping de l'itemid
    COALESCE(
        (SELECT concept_id FROM concept 
         WHERE concept_code = o.itemid::text 
         AND vocabulary_id = 'MIMIC d_items' LIMIT 1), 
        0
    ),
    CAST(o.charttime AS DATE),
    o.charttime,
    32817,
    o.value,
    o.valueuom,
    v.visit_occurrence_id,
    o.itemid::text
FROM outputevents o
LEFT JOIN visit_occurrence v ON o.hadm_id::text = v.visit_source_value;


---provider
CREATE TABLE provider (
    provider_id                 integer NOT NULL,
    provider_name               text,
    npi                         text,
    dea                         text,
    specialty_concept_id        integer,
    care_site_id                integer,
    year_of_birth               integer,
    gender_concept_id           integer,
    provider_source_value       text,
    specialty_source_value      text,
    specialty_source_concept_id integer,
    gender_source_value         text,
    gender_source_concept_id    integer
);

INSERT INTO provider (
    provider_id,
    provider_source_value,
    specialty_concept_id,
    gender_concept_id,
    specialty_source_value
)
SELECT 
    caregiver_id AS provider_id,
    caregiver_id::text AS provider_source_value,
    
    -- ATHENA : On met 0 (Unknown) pour la spécialité si on n'a pas la table de référence
    COALESCE((SELECT concept_id FROM concept WHERE concept_id = 0), 0) AS specialty_concept_id,
    
    -- ATHENA : On met 0 (Unknown) pour le genre
    COALESCE((SELECT concept_id FROM concept WHERE concept_id = 0), 0) AS gender_concept_id,
    
    'Unknown Specialty' AS specialty_source_value

FROM datetimeevents
WHERE caregiver_id IS NOT NULL
GROUP BY caregiver_id;


---Drug exposure
CREATE TABLE drug_exposure (
    drug_exposure_id              SERIAL,
    person_id                     integer,
    drug_concept_id               integer,
    drug_exposure_start_date      date,
    drug_exposure_start_datetime  timestamp,
    drug_exposure_end_date        date,
    drug_exposure_end_datetime    timestamp,
    verbatim_end_date             date,
    drug_type_concept_id          integer,
    stop_reason                   text,
    refills                       integer,
    quantity                      numeric,
    days_supply                   integer,
    sig                           text,
    route_concept_id              integer,
    lot_number                    text,
    provider_id                   integer,
    visit_occurrence_id           integer,
    visit_detail_id               integer,
    drug_source_value             text,
    drug_source_concept_id        integer,
    route_source_value            text,
    dose_unit_source_value        text
);

-- Index sur le vocabulaire Athena (Indispensable pour le mapping) PSQ TROP LONG SI NN
CREATE INDEX IF NOT EXISTS idx_concept_code ON concept (concept_code);
CREATE INDEX IF NOT EXISTS idx_concept_vocabulary ON concept (vocabulary_id);

-- Index sur tes visites (Indispensable pour le JOIN)
CREATE INDEX IF NOT EXISTS idx_visit_source_val ON visit_occurrence (visit_source_value);

INSERT INTO drug_exposure (
    person_id, drug_concept_id, drug_exposure_start_date, drug_exposure_start_datetime,
    drug_exposure_end_date, drug_exposure_end_datetime, quantity, 
    dose_unit_source_value, sig, visit_occurrence_id,
    drug_type_concept_id, drug_source_value
)
SELECT 
    i.subject_id,
    COALESCE(c.concept_id, 0),
    CAST(i.starttime AS DATE), i.starttime,
    CAST(i.endtime AS DATE), i.endtime,
    i.amount,
    (COALESCE(i.rateuom, '') || ' ' || COALESCE(i.amountuom, '')),
    i.rate::text,
    v.visit_occurrence_id,
    32817, -- EHR Administration
    i.itemid::text
FROM ingredientevents i
LEFT JOIN visit_occurrence v ON i.hadm_id::text = v.visit_source_value
LEFT JOIN concept c ON c.concept_code = i.itemid::text 
                   AND c.vocabulary_id = 'MIMIC d_items';

INSERT INTO drug_exposure (
    person_id, drug_concept_id, drug_exposure_start_date, drug_exposure_start_datetime,
    drug_exposure_end_date, drug_exposure_end_datetime, quantity, 
    dose_unit_source_value, sig, visit_occurrence_id,
    drug_type_concept_id, drug_source_value
)
SELECT 
    inp.subject_id,
    COALESCE(c.concept_id, 0),
    CAST(inp.starttime AS DATE), inp.starttime,
    CAST(inp.endtime AS DATE), inp.endtime,
    COALESCE(inp.amount, inp.totalamount),
    (COALESCE(inp.amountuom, '') || ' ' || COALESCE(inp.totalamountuom, '') || ' ' || COALESCE(inp.rateuom, '')),
    inp.rate::text,
    v.visit_occurrence_id,
    32817,
    inp.itemid::text
FROM inputevents inp
LEFT JOIN visit_occurrence v ON inp.hadm_id::text = v.visit_source_value
LEFT JOIN concept c ON c.concept_code = inp.itemid::text 
                   AND c.vocabulary_id = 'MIMIC d_items';


procedure_occurence:
CREATE TABLE procedure_occurrence (
    procedure_occurrence_id       SERIAL,
    person_id                     integer,
    procedure_concept_id          integer,
    procedure_date                date,
    procedure_datetime            timestamp,
    procedure_end_date            date,
    procedure_end_datetime        timestamp,
    procedure_type_concept_id     integer,
    modifier_concept_id           integer,
    quantity                      numeric,
    provider_id                   integer,
    visit_occurrence_id           integer,
    visit_detail_id               integer,
    procedure_source_value        text,
    procedure_source_concept_id   integer,
    modifier_source_value         text
);

INSERT INTO procedure_occurrence (
    person_id,
    procedure_concept_id,
    procedure_date,
    procedure_datetime,
    procedure_end_date,
    procedure_end_datetime,
    procedure_type_concept_id,
    quantity,
    visit_occurrence_id,
    procedure_source_value
)
SELECT 
    p.subject_id,
    -- ATHENA : Mapping de l'itemid vers un concept de procédure
    COALESCE(c.concept_id, 0),
    CAST(p.starttime AS DATE),
    p.starttime,
    CAST(p.endtime AS DATE),
    p.endtime,
    32817, -- EHR record
    p.value, -- La quantité selon ton Rabbit
    v.visit_occurrence_id,
    p.itemid::text
FROM procedureevents p
LEFT JOIN visit_occurrence v ON p.hadm_id::text = v.visit_source_value
LEFT JOIN concept c ON c.concept_code = p.itemid::text 
                   AND c.vocabulary_id = 'MIMIC d_items';