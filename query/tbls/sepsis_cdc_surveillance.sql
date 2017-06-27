

-- CDC Epicenters complete surveillance criteria
-- Among patients with suspected infection only those who
-- met specific organ dysfunction criteria

-- Suspected infection: antibiotics + blood culture
-- requires:
--  abx_poe_list
--  abx_micro_poe

-- Organ dysfunction: modified from Rhee et al. by Seymour et al.
-- Rhee C, Kadri S, Huang SS, et al. Objective Sepsis Surveillance Using Electronic Clinical Data. Infect Control Hosp Epidemiol. Nov 3 2015:1-9.
-- Seymour 2016 Application

-- modified organ dysfunction required one of the following to be present:
-- a.	Mechanical ventilation for more than 24 hrs hospital stay (present/absent)
--     if the patient expired while mechanically ventilated before 48 hrs hospital stay, this was coded as present.
--     Non-invasive mechanical ventilation was not included.
-- b.	Vasopressor use (present/absent) during hospital stay
-- c.	Rise in serum creatinine >=0.5 from lowest value recorded during hospitalization (present/absent).
--     If patients had discharge diagnosis of end-stage renal disease (ICD9-CM code=585.6), this was coded as absent.
-- d.	Platelet count <100 cells/µL and ≥ 50% decline from highest value recorded during hospital stay (present/absent)
-- e.	Total bilirubin ≥ 2.0 mg/dL and increase by 100% from lowest value recorded during hospital stay (present/absent)
-- f.	INR >1.5 and ≥0.5 increase from lowest value recorded during hospital stay (present/absent)

-- In Seymour et al., the time period for creatinine, bilirubin, INR, or platelet changes to occur was within 48 hrs prior and 24 hrs after the onset of infection.
-- We modify this to [-6,24] hours from ICU admission

-- mech vent
-- vasopressor
-- creatinine
-- platelet
-- bilirubin
-- INR

DROP TABLE IF EXISTS sepsis_cdc_surveillance cascade;
CREATE TABLE sepsis_cdc_surveillance AS
-- get lowest creatinine, platelet, bili, and INR
-- get all labs back until hospital admit
with labs_stg1 as
(
  -- begin query that extracts the data
  select ie.icustay_id, ie.hadm_id
  -- here we assign labels to ITEMIDs
  -- this also fuses together multiple ITEMIDs containing the same data
  , case
        when itemid = 50885 then 'BILIRUBIN'
        when itemid = 50912 then 'CREATININE'
        when itemid = 51265 then 'PLATELET'
        when itemid = 51237 then 'INR'
      else null
    end as label
  -- add in some sanity checks on the values
  -- the where clause below requires all valuenum to be > 0, so these are only upper limit checks
  , case
      when itemid = 50885 and valuenum >   150 then null -- mg/dL 'BILIRUBIN'
      when itemid = 50912 and valuenum >   150 then null -- mg/dL 'CREATININE'
      when itemid = 51265 and valuenum > 10000 then null -- K/uL 'PLATELET'
      when itemid = 51237 and valuenum >    50 then null -- 'INR'
    else le.valuenum
    end as valuenum
  , min(valuenum) OVER (PARTITION BY ie.icustay_id, le.itemid) as valuenum_min
  , max(valuenum) OVER (PARTITION BY ie.icustay_id, le.itemid) as valuenum_max
  , case when le.charttime >= ie.intime - interval '6' hour
          and le.charttime <= ie.intime + interval '1' day
        then 1 else 0 end as firstday
  from icustays ie
  inner join admissions adm
    on ie.hadm_id = adm.hadm_id
  inner join labevents le
    on adm.hadm_id = le.hadm_id
    and le.charttime >= adm.admittime
    and le.charttime <= adm.dischtime
  where le.itemid in
  (
  -- comment is: LABEL | CATEGORY | FLUID | NUMBER OF ROWS IN LABEVENTS
  50885, -- BILIRUBIN, TOTAL | CHEMISTRY | BLOOD | 238277
  50912, -- CREATININE | CHEMISTRY | BLOOD | 797476
  51265, -- PLATELET COUNT | HEMATOLOGY | BLOOD | 778444
  51237  -- INR(PT) | HEMATOLOGY | BLOOD | 471183
  )
  and valuenum is not null and valuenum > 0 -- lab values cannot be 0 and cannot be negative
)
-- now determine whether a lab value has changed sufficiently to indicate organ dysfunction
, labs_stg2 as
(
  select
    ls.icustay_id, ls.hadm_id
    -- c.	Rise in serum creatinine >=0.5 from lowest value recorded during hospitalization (present/absent).
    --     If patients had discharge diagnosis of end-stage renal disease (ICD9-CM code=585.6), this was coded as absent.
    , max(case
          when esrd.hadm_id is not null then 0
          when label = 'CREATININE' and firstday = 1 and valuenum >= valuenum_min + 0.5 then 1
        else 0
      end) as renal
    -- d.	Platelet count <100 cells/µL and ≥ 50% decline from highest value recorded during hospital stay (present/absent)
    , max(case when label = 'PLATELET' and firstday = 1 and valuenum < 100 and valuenum <= 0.5*valuenum_max then 1
        else 0
      end) as hematologic
    -- e.	Total bilirubin ≥ 2.0 mg/dL and increase by 100% from lowest value recorded during hospital stay (present/absent)
    , max(case when label = 'BILIRUBIN' and firstday = 1 and valuenum >= 2.0 and valuenum >= 2*valuenum_min then 1
        else 0
      end) as hepatic
    -- f.	INR >1.5 and ≥0.5 increase from lowest value recorded during hospital stay (present/absent)
    , max(case when label = 'INR' and firstday = 1 and valuenum > 1.5 and valuenum >= valuenum_min+0.5 then 1
        else 0
      end) as coagulation
  from labs_stg1 ls
  left join
  (
    select hadm_id from diagnoses_icd where icd9_code = '5856'
  ) esrd
    on ls.hadm_id = esrd.hadm_id
  group by ls.icustay_id, ls.hadm_id
)
-- a.	Mechanical ventilation for more than 24 hrs hospital stay (present/absent)
--     if the patient expired while mechanically ventilated before 48 hrs hospital stay, this was coded as present.
--     Non-invasive mechanical ventilation was not included.
, vd_sum as
(
  select icustay_id
    , sum(extract(epoch from starttime-endtime))/60.0/60.0 as total_duration
    , max(endtime) as endtime
  from ventdurations
  group by icustay_id
)
, vent as
(
  select vd.icustay_id
    , case  when vd.total_duration >= 24.0 then 1
            -- if vent settings occurred within 6 hours of death, assume vented when patient expired
            when vd.endtime > adm.deathtime - interval '6' hour then 1
          else 0 end as respiratory
  from vd_sum vd
  inner join icustays ie
    on vd.icustay_id = ie.icustay_id
  inner join admissions adm
    on ie.hadm_id = adm.hadm_id
)
-- b.	Vasopressor use (present/absent) during hospital stay
, vaso as
(
  select distinct icustay_id, 1 as cardiovascular
  from vasopressordurations
)
-- group it all
select ie.icustay_id
, case
   WHEN si.suspected_infection_time is null then 0
   WHEN si.suspected_infection_time
    between ie.intime - interval '1' day and ie.intime + interval '1' day
    AND
    (
      coalesce(labs.renal,0) = 1
     OR coalesce(labs.hematologic,0) = 1
     OR coalesce(labs.hepatic,0) = 1
     OR coalesce(labs.coagulation,0) = 1
     OR coalesce(vent.respiratory,0) = 1
     OR coalesce(vaso.cardiovascular,0) = 1
   )
     then 1
  else 0 end sepsis
-- simple rule that requires fewer labs to be recorded
, case
   WHEN si.suspected_infection_time is null then 0
   WHEN si.suspected_infection_time
    between ie.intime - interval '1' day and ie.intime + interval '1' day
    AND
    (
      coalesce(labs.renal,0) = 1
     OR coalesce(vent.respiratory,0) = 1
     OR coalesce(vaso.cardiovascular,0) = 1
   )
     then 1
  else 0 end sepsis_simple
, si.suspected_infection_time
, coalesce(labs.renal,0) as renal
, coalesce(labs.hematologic,0) as hematologic
, coalesce(labs.hepatic,0) as hepatic
, coalesce(labs.coagulation,0) as coagulation
, coalesce(vent.respiratory,0) as respiratory
, coalesce(vaso.cardiovascular,0) as cardiovascular
from icustays ie
left join labs_stg2 labs
  on ie.icustay_id = labs.icustay_id
left join vent
  on ie.icustay_id = vent.icustay_id
left join vaso
  on ie.icustay_id = vaso.icustay_id
left join suspinfect_poe si
  on ie.icustay_id = si.icustay_id
