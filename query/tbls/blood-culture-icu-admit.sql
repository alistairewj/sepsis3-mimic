DROP TABLE IF EXISTS blood_culture_icu_admit cascade;
CREATE TABLE blood_culture_icu_admit AS
with me as
(
  select hadm_id
    , chartdate, charttime
    , spec_type_desc
    , max(case when org_name is not null and org_name != '' then 1 else 0 end) as PositiveCulture
  from `physionet-data.mimiciii_clinical.microbiologyevents`
  group by hadm_id, chartdate, charttime, spec_type_desc
)
select
    ie.icustay_id
  , min(coalesce(charttime, chartdate)) as charttime
  , max(case when me.hadm_id is not null then 1 else 0 end) as blood_culture
  , max(case when org_name is not null and org_name != '' then 1 else 0 end) as PositiveCulture
from `physionet-data.mimiciii_clinical.icustays` ie
left join `physionet-data.mimiciii_clinical.microbiologyevents` me
  on ie.hadm_id = me.hadm_id
  and (
      me.charttime between DATETIME_SUB(ie.intime, INTERVAL 1 DAY) and DATETIME_ADD(ie.intime, INTERVAL 1 DAY)
  OR  me.chartdate between DATETIME_TRUNC(DATETIME_SUB(ie.intime, INTERVAL 1 DAY), DAY) and DATETIME_ADD(ie.intime, INTERVAL 1 DAY)
  )
group by ie.icustay_id;
