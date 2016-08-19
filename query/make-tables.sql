-- As the script is generating many tables, it may take some time.

BEGIN;
-- ----------------------------- --
-- ---------- STAGE 1 ---------- --
-- ----------------------------- --

\i tbls/suspicion-of-infection.sql

-- Generate the views which the severity scores are based on
\i tbls/urine-output-infect-time.sql
\i tbls/vitals-infect-time.sql
\i tbls/gcs-infect-time.sql
\i tbls/labs-infect-time.sql
\i tbls/blood-gas-infect-time.sql
\i tbls/blood-gas-arterial-infect-time.sql

\i tbls/vaso-dur.sql
\i ../mimic-code/etc/firstday/weight-first-day.sql -- TODO: add to mimic-code
\i ../mimic-code/etc/firstday/height-first-day.sql -- TODO: add to mimic-code
\i ../mimic-code/comorbidity/postgres/elixhauser-ahrq-v37-with-drg.sql
\i ../mimic-code/sepsis/angus.sql

-- ----------------------------- --
-- ---------- STAGE 2 ---------- --
-- ----------------------------- --

-- TODO: generate all severity scores

\i ../mimic-code/severityscores/mlods.sql
\i ../mimic-code/severityscores/sirs.sql -- TODO: add to mimic-code
\i ../mimic-code/severityscores/qsofa.sql -- TODO: add to mimic-code

-- Generate the scores
\i tbls/sofa-si.sql
\i tbls/sirs-si.sql
\i tbls/lods-si.sql
\i tbls/qsofa-si.sql
\i tbls/mlods-si.sql


\i tbls/qsofa-admission.sql

\i tbls/blood-gas-admission.sql
\i tbls/sirs-admission.sql

-- Generate the final table
\i tbls/sepsis3.sql

COMMIT;
