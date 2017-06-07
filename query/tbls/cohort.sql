DROP TABLE IF EXISTS sepsis3_cohort CASCADE;
CREATE TABLE sepsis3_cohort AS
with serv as
(
    select hadm_id, curr_service
    , ROW_NUMBER() over (partition by hadm_id order by transfertime) as rn
    from services
)
, t1 as
(
select ie.icustay_id, ie.hadm_id
    , ie.intime, ie.outtime
    , round((cast(adm.admittime as date) - cast(pat.dob as date)) / 365.242, 4) as age
    , pat.gender
    , adm.ethnicity
    , ie.dbsource
    -- used to get first ICUSTAY_ID
    , ROW_NUMBER() over (partition by ie.subject_id order by intime) as rn

    -- exclusions
    , s.curr_service as first_service
    , adm.HAS_CHARTEVENTS_DATA

    -- suspicion of infection
    , case when si.suspected_infection_time is not null then 1 else 0 end
        as suspected_of_infection
    , si.suspected_infection_time
    , extract(EPOCH from ie.intime - si.suspected_infection_time)
          / 60.0 / 60.0 / 24.0 as suspected_infection_time_days
    , si.specimen
    , si.positiveculture

    -- suspicion that *only* works for metavision data
    , case when smv.suspected_infection_time is not null then 1 else 0 end
        as suspected_of_infection_mv
    , smv.suspected_infection_time as suspected_infection_time_mv
    , extract(EPOCH from ie.intime - smv.suspected_infection_time)
          / 60.0 / 60.0 / 24.0 as suspected_infection_time_mv_days
    , smv.specimen as specimen_mv
    , smv.positiveculture as positiveculture_mv

    , extract(EPOCH from ie.intime - smv.si_starttime)
          / 60.0 / 60.0 / 24.0 as si_starttime_days
    , extract(EPOCH from ie.intime - smv.si_endtime)
          / 60.0 / 60.0 / 24.0 as si_endtime_days

    -- suspicion using POE
    , case when spoe.suspected_infection_time is not null then 1 else 0 end
        as suspected_of_infection_poe
    , spoe.suspected_infection_time as suspected_infection_time_poe
    , extract(EPOCH from ie.intime - spoe.suspected_infection_time)
          / 60.0 / 60.0 / 24.0 as suspected_infection_time_poe_days
    , spoe.specimen as specimen_poe
    , spoe.positiveculture as positiveculture_poe

    , case when d1poe.suspected_infection_time is not null then 1 else 0 end
        as suspected_of_infection_d1poe
    , d1poe.suspected_infection_time as suspected_infection_time_d1poe
    , extract(EPOCH from ie.intime - d1poe.suspected_infection_time)
          / 60.0 / 60.0 / 24.0 as suspected_infection_time_d1poe_days
    , d1poe.specimen as specimen_d1poe
    , d1poe.positiveculture as positiveculture_d1poe

    -- suspicion using POE only with IV abx
    , case when spiv.suspected_infection_time is not null then 1 else 0 end
        as suspected_of_infection_piv
    , spiv.suspected_infection_time as suspected_infection_time_piv
    , extract(EPOCH from ie.intime - spiv.suspected_infection_time)
          / 60.0 / 60.0 / 24.0 as suspected_infection_time_piv_days
    , spiv.specimen as specimen_piv
    , spiv.positiveculture as positiveculture_piv

from icustays ie
inner join admissions adm
    on ie.hadm_id = adm.hadm_id
inner join patients pat
    on ie.subject_id = pat.subject_id
left join serv s
    on ie.hadm_id = s.hadm_id
    and s.rn = 1
left join suspinfect si
  on ie.icustay_id = si.icustay_id
left join SUSPINFECT_MV smv
  on ie.icustay_id = smv.icustay_id
left join suspinfect_poe spoe
  on ie.icustay_id = spoe.icustay_id
left join suspinfect_poe_day1 d1poe
  on ie.icustay_id = d1poe.icustay_id
left join suspinfect_poe_iv spiv
  on ie.icustay_id = spiv.icustay_id
)
select
    t1.hadm_id, t1.icustay_id
  , t1.intime, t1.outtime

  -- set de-identified ages to median of 91.4
  , case when age > 89 then 91.4 else age end as age
  , gender
  , ethnicity
  , first_service
  , dbsource

  , suspected_of_infection
  , suspected_infection_time
  , suspected_infection_time_days
  , specimen
  , positiveculture

  -- suspicion that *only* works for metavision data
  , suspected_of_infection_mv
  , suspected_infection_time_mv
  , suspected_infection_time_mv_days
  , specimen_mv
  , positiveculture_mv

  -- suspicion using POE
  , suspected_of_infection_poe
  , suspected_infection_time_poe
  , suspected_infection_time_poe_days
  , specimen_poe
  , positiveculture_poe

  -- suspicion using POE 1st day
  , suspected_of_infection_d1poe
  , suspected_infection_time_d1poe
  , suspected_infection_time_d1poe_days
  , specimen_d1poe
  , positiveculture_d1poe

  -- suspicion using POE (IV)
  , suspected_of_infection_piv
  , suspected_infection_time_piv
  , suspected_infection_time_piv_days
  , specimen_piv
  , positiveculture_piv

  -- exclusions
  , case when t1.rn = 1 then 0 else 1 end as exclusion_secondarystay
  , case when t1.age <= 16 then 1 else 0 end as exclusion_nonadult
  , case when t1.first_service in ('CSURG','VSURG','TSURG') then 1 else 0 end as exclusion_csurg
  , case when t1.dbsource != 'metavision' then 1 else 0 end as exclusion_carevue
  , case when t1.suspected_infection_time_poe is not null
          and t1.suspected_infection_time_poe < (t1.intime-interval '1' day) then 1
      else 0 end as exclusion_early_suspicion
  , case when t1.suspected_infection_time_poe is not null
          and t1.suspected_infection_time_poe > (t1.intime+interval '1' day) then 1
      else 0 end as exclusion_late_suspicion
  , case when t1.HAS_CHARTEVENTS_DATA = 0 then 1
         when t1.intime is null then 1
         when t1.outtime is null then 1
      else 0 end as exclusion_bad_data
  -- , case when t1.suspected_of_infection = 0 then 1 else 0 end as exclusion_suspicion

  -- the above flags are used to summarize patients excluded
  -- below flag is used to actually exclude patients in future queries
  , case when
             t1.rn != 1
          or t1.age <= 16
          or t1.first_service in ('CSURG','VSURG','TSURG')
          or t1.HAS_CHARTEVENTS_DATA = 0
          or t1.intime is null
          or t1.outtime is null
          or t1.dbsource != 'metavision'
          or (
                  t1.suspected_infection_time_poe is not null
              and t1.suspected_infection_time_poe < (t1.intime-interval '1' day)
            )
          or (
                  t1.suspected_infection_time_poe is not null
              and t1.suspected_infection_time_poe > (t1.intime+interval '1' day)
            )
          -- or t1.suspected_of_infection = 0
            then 1
        else 0 end as excluded
from t1
order by t1.icustay_id;
