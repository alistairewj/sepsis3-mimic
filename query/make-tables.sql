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

-- ----------------------------- --
-- ---------- STAGE 2 ---------- --
-- ----------------------------- --

-- Generate the scores
\i tbls/sofa-si.sql
\i tbls/sirs-si.sql
\i tbls/lods-si.sql
\i tbls/qsofa-si.sql
\i tbls/mlods-si.sql

\i tbls/qsofa-admission.sql

-- Generate the final table
\i tbls/sepsis3.sql

COMMIT;
