-- As the script is generating many tables, it may take some time.

\c mimic;
set search_path to mimiciii;

BEGIN;
-- ----------------------------- --
-- ---------- STAGE 1 ---------- --
-- ----------------------------- --

\i tbls/suspicion-of-infection.sql

-- Generate the views which the severity scores are based on (at time of infection)
\i tbls/urine-output-infect-time.sql
\i tbls/vitals-infect-time.sql
\i tbls/gcs-infect-time.sql
\i tbls/labs-infect-time.sql
\i tbls/blood-gas-infect-time.sql
\i tbls/blood-gas-arterial-infect-time.sql
\i tbls/vaso-dur.sql

-- Generate the views which the severity scores are based on (first 24 hours)
\i ../mimic-code/etc/firstday/urine-output-first-day.sql
\i ../mimic-code/etc/firstday/ventilation-first-day.sql
\i ../mimic-code/etc/firstday/vitals-first-day.sql
\i ../mimic-code/etc/firstday/gcs-first-day.sql
\i ../mimic-code/etc/firstday/labs-first-day.sql
\i ../mimic-code/etc/firstday/blood-gas-first-day.sql
\i ../mimic-code/etc/firstday/blood-gas-first-day-arterial.sql

\i ../mimic-code/etc/ventilation-durations.sql
\i ../mimic-code/etc/echo-data.sql
\i ../mimic-code/etc/firstday/weight-first-day.sql
\i ../mimic-code/etc/firstday/height-first-day.sql
\i ../mimic-code/comorbidity/postgres/elixhauser-ahrq-v37-with-drg.sql
\i ../mimic-code/sepsis/angus.sql

-- ----------------------------- --
-- ---------- STAGE 2 ---------- --
-- ----------------------------- --

-- Severity scores during the first 24 hours
\i ../mimic-code/severityscores/lods.sql
\i ../mimic-code/severityscores/mlods.sql
\i ../mimic-code/severityscores/sirs.sql
\i ../mimic-code/severityscores/qsofa.sql
\i ../mimic-code/severityscores/sofa.sql

-- Severity scores at the time of suspected infection
\i tbls/sofa-si.sql
\i tbls/sirs-si.sql
\i tbls/lods-si.sql
\i tbls/qsofa-si.sql
\i tbls/mlods-si.sql

-- Severity scores on admission
\i tbls/qsofa-admission.sql
\i tbls/blood-gas-admission.sql
\i tbls/sirs-admission.sql

-- Generate the final table
\i tbls/sepsis3.sql

COMMIT;
