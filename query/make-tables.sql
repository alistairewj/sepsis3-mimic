-- As the script is generating many tables, it may take some time.

-- We assume the database and the search path are set correctly.
-- You can set the search path as follows:
-- SET SEARCH_PATH TO public,mimiciii;
-- This will create tables on public and read tables from mimiciii

BEGIN;
-- ----------------------------- --
-- ---------- STAGE 1 ---------- --
-- ----------------------------- --

\i tbls/abx-poe-list.sql
\i tbls/abx-micro-prescription.sql
\i tbls/suspicion-of-infection.sql

-- blood cultures around ICU admission
\i tbls/blood-culture-icu-admit.sql

-- generate cohort
\i tbls/cohort.sql

-- generate sepsis definitions
\i ../mimic-code/concepts/sepsis/angus.sql
\i ../mimic-code/concepts/sepsis/martin.sql
\i ../mimic-code/concepts/sepsis/explicit.sql


-- -- Generate the views which the severity scores are based on (at time of infection)
-- \i tbls/urine-output-infect-time.sql
-- \i tbls/vitals-infect-time.sql
-- \i tbls/gcs-infect-time.sql
-- \i tbls/labs-infect-time.sql
-- \i tbls/blood-gas-infect-time.sql
-- \i tbls/blood-gas-arterial-infect-time.sql
-- \i tbls/vaso-dur.sql

-- Generate the views which the severity scores are based on (first 24 hours)
\i ../mimic-code/concepts/durations/vasopressor-durations.sql
\i ../mimic-code/concepts/durations/ventilation-durations.sql

\i ../mimic-code/concepts/firstday/urine-output-first-day.sql
\i ../mimic-code/concepts/firstday/ventilation-first-day.sql
\i ../mimic-code/concepts/firstday/vitals-first-day.sql
\i ../mimic-code/concepts/firstday/gcs-first-day.sql
\i ../mimic-code/concepts/firstday/labs-first-day.sql
\i ../mimic-code/concepts/firstday/blood-gas-first-day.sql
\i ../mimic-code/concepts/firstday/blood-gas-first-day-arterial.sql

\i ../mimic-code/concepts/echo-data.sql
\i ../mimic-code/concepts/firstday/weight-first-day.sql
\i ../mimic-code/concepts/firstday/height-first-day.sql
\i ../mimic-code/concepts/comorbidity/elixhauser-ahrq-v37-with-drg.sql

-- ----------------------------- --
-- ---------- STAGE 2 ---------- --
-- ----------------------------- --

-- Severity scores during the first 24 hours
\i ../mimic-code/concepts/severityscores/lods.sql
\i ../mimic-code/concepts/severityscores/mlods.sql
\i ../mimic-code/concepts/severityscores/sirs.sql
\i ../mimic-code/concepts/severityscores/qsofa.sql
\i ../mimic-code/concepts/severityscores/sofa.sql

-- -- Severity scores at the time of suspected infection
-- \i tbls/sofa-si.sql
-- \i tbls/sirs-si.sql
-- \i tbls/lods-si.sql
-- \i tbls/qsofa-si.sql
-- \i tbls/mlods-si.sql

-- -- Severity scores on admission
-- \i tbls/qsofa-admission.sql
-- \i tbls/blood-gas-admission.sql
-- \i tbls/sirs-admission.sql

-- ----------------------------- --
-- ---------- STAGE 3 ---------- --
-- ----------------------------- --
-- Some sepsis criteria require the severity scores (e.g. SIRS)
\i tbls/sepsis_cdc_surveillance.sql
\i tbls/sepsis_nqf_0500.sql

-- Generate the final table
\i tbls/sepsis3.sql

COMMIT;
