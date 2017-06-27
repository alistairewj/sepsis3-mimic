-- only works for metavision as carevue does not accurately document antibiotics
DROP TABLE IF EXISTS suspinfect_poe_day1 CASCADE;
CREATE TABLE suspinfect_poe_day1 as
with mv as
(
  select hadm_id
  , mv.drug as first_antibiotic_name
  , startdate as first_antibiotic_time
  , enddate as first_antibiotic_endtime
  from prescriptions mv
  inner join abx_poe_list ab
      on mv.drug = ab.drug
)
, ab_tbl as
(
  select
        ie.subject_id, ie.hadm_id, ie.icustay_id
      , ie.intime, ie.outtime
      , mv.first_antibiotic_name
      , mv.first_antibiotic_time
      , mv.first_antibiotic_endtime
      , ROW_NUMBER() over
      (
        partition by ie.icustay_id
        order by mv.first_antibiotic_time, mv.first_antibiotic_endtime
      ) as rn
  from icustays ie
  left join mv
      on ie.hadm_id = mv.hadm_id
      and mv.first_antibiotic_time
      between ie.intime - interval '1' day and ie.outtime
)
, me as
(
  select hadm_id
    , chartdate, charttime
    , spec_type_desc
    , max(case when org_name is not null and org_name != '' then 1 else 0 end) as PositiveCulture
  from microbiologyevents
  group by hadm_id, chartdate, charttime, spec_type_desc
)
, ab_fnl as
(
  select
      ab_tbl.icustay_id, ab_tbl.intime, ab_tbl.outtime
    , ab_tbl.first_antibiotic_name
    , ab_tbl.first_antibiotic_time
    , me72.charttime as last72_charttime
    , me72.chartdate as last72_chartdate
    , me24.charttime as next24_charttime
    , me24.chartdate as next24_chartdate

    , me72.positiveculture as last72_positiveculture
    , me72.spec_type_desc as last72_specimen
    , me24.positiveculture as next24_positiveculture
    , me24.spec_type_desc as next24_specimen

    , ROW_NUMBER() over
    (
      partition by ab_tbl.icustay_id
      order by coalesce(me72.charttime, me24.charttime, me72.chartdate)
    )
        as rn
  from ab_tbl
  -- blood culture in last 72 hours
  left join me me72
    on ab_tbl.hadm_id = me72.hadm_id
    and ab_tbl.first_antibiotic_time is not null
    and
    (
      -- if charttime is available, use it
      (
          ab_tbl.first_antibiotic_time > me72.charttime
      and ab_tbl.first_antibiotic_time <= me72.charttime + interval '72' hour
      )
      OR
      (
      -- if charttime is not available, use chartdate
          me72.charttime is null
      and ab_tbl.first_antibiotic_time > me72.chartdate
      and ab_tbl.first_antibiotic_time < me72.chartdate + interval '96' hour -- could equally do this with a date_trunc, but that's less portable
      )
    )
  -- blood culture in subsequent 24 hours
  left join me me24
    on ab_tbl.hadm_id = me24.hadm_id
    and ab_tbl.first_antibiotic_time is not null
    and me24.charttime is not null
    and
    (
      -- if charttime is available, use it
      (
          ab_tbl.first_antibiotic_time > me24.charttime - interval '24' hour
      and ab_tbl.first_antibiotic_time <= me24.charttime
      )
      OR
      (
      -- if charttime is not available, use chartdate
          me24.charttime is null
      and ab_tbl.first_antibiotic_time > me24.chartdate
      and ab_tbl.first_antibiotic_time <= me24.chartdate + interval '24' hour
      )
    )
)
, ab_laststg as
(
select
  icustay_id
  , first_antibiotic_name
  , first_antibiotic_time
  -- time of suspected infection: either the culture time (if before antibiotic), or the antibiotic time
  , case
      when first_antibiotic_time > intime + interval '48' hour then null
      when last72_charttime is not null
        then last72_charttime
      when next24_charttime is not null or last72_chartdate is not null
        then first_antibiotic_time
    else null
  end as suspected_infection_time
  -- the specimen that was cultured
  , case
      when first_antibiotic_time > intime + interval '48' hour then null
      when last72_charttime is not null or last72_chartdate is not null
        then last72_specimen
      when next24_charttime is not null
        then next24_specimen
    else null
  end as specimen
  -- whether the cultured specimen ended up being positive or not
  , case
      when first_antibiotic_time > intime + interval '48' hour then null
      when last72_charttime is not null or last72_chartdate is not null
        then last72_positiveculture
      when next24_charttime is not null
        then next24_positiveculture
    else null
  end as positiveculture
from ab_fnl
where rn = 1
)
select
  icustay_id, suspected_infection_time
  -- the below two fields are used to extract data - modifying them facilitates sensitivity analyses
  , suspected_infection_time - interval '48' hour as si_starttime
  , suspected_infection_time + interval '24' hour as si_endtime
  , specimen, positiveculture
  , first_antibiotic_name
  , first_antibiotic_time
from ab_laststg
order by icustay_id;
