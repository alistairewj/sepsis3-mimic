DROP TABLE IF EXISTS blood_culture_icu_admit cascade;
CREATE TABLE blood_culture_icu_admit AS
with me as
(
  select hadm_id
    , chartdate, charttime
    , spec_type_desc
    , max(case when org_name is not null and org_name != '' then 1 else 0 end) as PositiveCulture
  from microbiologyevents
  group by hadm_id, chartdate, charttime, spec_type_desc
)
select
    ie.icustay_id
  , min(coalesce(charttime, chartdate)) as charttime
  , max(case when me.hadm_id is not null then 1 else 0 end) as blood_culture
  , max(case when org_name is not null and org_name != '' then 1 else 0 end) as PositiveCulture
from icustays ie
left join microbiologyevents me
  on ie.hadm_id = me.hadm_id
  and (
      me.charttime between ie.intime - interval '1' day and ie.intime + interval '1' day
  OR  me.chartdate between date_trunc('day',ie.intime - interval '1' day) and ie.intime + interval '1' day
  )
group by ie.icustay_id;
