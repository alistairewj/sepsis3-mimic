-- ------------------------------------------------------------------
-- Title: Quick Sequential Organ Failure Assessment (qSOFA)
-- Originally written by: Alistair Johnson
-- Contact: aewj [at] mit [dot] edu
-- ------------------------------------------------------------------

-- This query extracts the quick sequential organ failure assessment (formally: sepsis-related organ failure assessment).
-- This score was a recent revision of SOFA, aiming to detect patients at risk of sepsis.

-- Reference for qSOFA:
--    Singer M, et al. The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3)
--    Seymour CW, et al. Assessment of Clinical Criteria for Sepsis: For the Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3)

-- Variables used in qSOFA:
--  GCS, respiratory rate, systolic blood pressure

DROP MATERIALIZED VIEW IF EXISTS QSOFA_si CASCADE;
CREATE MATERIALIZED VIEW QSOFA_si AS
with scorecomp as
(
select s.icustay_id
  , v.SysBP_Min
  , v.RespRate_max
  , gcs.MinGCS
from suspinfect_poe s
left join vitals_si v
  on s.icustay_id = v.icustay_id
left join gcs_si gcs
  on s.icustay_id = gcs.icustay_id
where s.suspected_infection_time is not null
)
, scorecalc as
(
  -- Calculate the final score
  -- note that if the underlying data is missing, the component is null
  -- eventually these are treated as 0 (normal), but knowing when data is missing is useful for debugging
  select icustay_id
  , case
      when SysBP_Min is null then null
      when SysBP_Min   <= 100 then 1
      else 0 end
    as SysBP_score
  , case
      when MinGCS is null then null
      when MinGCS   <= 13 then 1
      else 0 end
    as GCS_score
  , case
      when RespRate_max is null then null
      when RespRate_max   >= 22 then 1
      else 0 end
    as RespRate_score
  from scorecomp
)
select icustay_id
, coalesce(SysBP_score,0)
 + coalesce(GCS_score,0)
 + coalesce(RespRate_score,0)
 as qSOFA
, SysBP_score
, GCS_score
, RespRate_score
from scorecalc s
order by icustay_id;
