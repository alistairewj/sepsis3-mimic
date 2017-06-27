DROP TABLE IF EXISTS sepsis3_cohort_cmp_susp_infect CASCADE;
CREATE TABLE sepsis3_cohort_cmp_susp_infect AS
select
    t1.hadm_id, t1.icustay_id
  , t1.intime, t1.outtime

  , age
  , gender
  , ethnicity
  , first_service
  , dbsource

  -- suspicion of infection
  , case when si.suspected_infection_time is not null then 1 else 0 end
      as suspected_of_infection
  , si.suspected_infection_time
  , extract(EPOCH from t1.intime - si.suspected_infection_time)
        / 60.0 / 60.0 / 24.0 as suspected_infection_time_days
  , si.specimen
  , si.positiveculture

  -- suspicion that *only* works for metavision data
  , case when smv.suspected_infection_time is not null then 1 else 0 end
      as suspected_of_infection_mv
  , smv.suspected_infection_time as suspected_infection_time_mv
  , extract(EPOCH from t1.intime - smv.suspected_infection_time)
        / 60.0 / 60.0 / 24.0 as suspected_infection_time_mv_days
  , smv.specimen as specimen_mv
  , smv.positiveculture as positiveculture_mv

  , extract(EPOCH from t1.intime - smv.si_starttime)
        / 60.0 / 60.0 / 24.0 as si_starttime_days
  , extract(EPOCH from t1.intime - smv.si_endtime)
        / 60.0 / 60.0 / 24.0 as si_endtime_days

  -- suspicion using POE
  , case when spoe.suspected_infection_time is not null then 1 else 0 end
      as suspected_of_infection_poe
  , spoe.suspected_infection_time as suspected_infection_time_poe
  , extract(EPOCH from t1.intime - spoe.suspected_infection_time)
        / 60.0 / 60.0 / 24.0 as suspected_infection_time_poe_days
  , spoe.specimen as specimen_poe
  , spoe.positiveculture as positiveculture_poe
  , spoe.antibiotic_time as antibiotic_time_poe

  , case when d1poe.suspected_infection_time is not null then 1 else 0 end
      as suspected_of_infection_d1poe
  , d1poe.suspected_infection_time as suspected_infection_time_d1poe
  , extract(EPOCH from t1.intime - d1poe.suspected_infection_time)
        / 60.0 / 60.0 / 24.0 as suspected_infection_time_d1poe_days
  , d1poe.specimen as specimen_d1poe
  , d1poe.positiveculture as positiveculture_d1poe

  -- suspicion using POE only with IV abx
  , case when spiv.suspected_infection_time is not null then 1 else 0 end
      as suspected_of_infection_piv
  , spiv.suspected_infection_time as suspected_infection_time_piv
  , extract(EPOCH from t1.intime - spiv.suspected_infection_time)
        / 60.0 / 60.0 / 24.0 as suspected_infection_time_piv_days
  , spiv.specimen as specimen_piv
  , spiv.positiveculture as positiveculture_piv

  -- exclusions
  , exclusion_secondarystay
  , exclusion_nonadult
  , exclusion_csurg
  , exclusion_carevue
  , exclusion_early_suspicion
  , exclusion_late_suspicion
  , exclusion_bad_data
  -- , case when t1.suspected_of_infection = 0 then 1 else 0 end as exclusion_suspicion

  -- the above flags are used to summarize patients excluded
  -- below flag is used to actually exclude patients in future queries
  , excluded

from sepsis3_cohort t1
left join suspinfect si
  on t1.icustay_id = si.icustay_id
left join SUSPINFECT_MV smv
  on t1.icustay_id = smv.icustay_id
left join suspinfect_poe spoe
  on t1.icustay_id = spoe.icustay_id
left join suspinfect_poe_day1 d1poe
  on t1.icustay_id = d1poe.icustay_id
left join suspinfect_poe_iv spiv
  on t1.icustay_id = spiv.icustay_id
order by t1.icustay_id;
