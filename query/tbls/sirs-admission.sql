-- ------------------------------------------------------------------
-- Title: Systemic inflammatory response syndrome (SIRS) criteria
-- Originally written by: Alistair Johnson
-- Contact: aewj [at] mit [dot] edu
-- ------------------------------------------------------------------

-- This query extracts the Systemic inflammatory response syndrome (SIRS) criteria
-- The criteria quantify the level of inflammatory response of the body
-- The score is calculated at admission (plus or minus 6 hours)

-- Reference for SIRS:
--    American College of Chest Physicians/Society of Critical Care Medicine Consensus Conference:
--    definitions for sepsis and organ failure and guidelines for the use of innovative therapies in sepsis"
--    Crit. Care Med. 20 (6): 864–74. 1992.
--    doi:10.1097/00003246-199206000-00025. PMID 1597042.

-- Variables used in SIRS:
--  Body temperature (min and max)
--  Heart rate (max)
--  Respiratory rate (max)
--  PaCO2 (min)
--  White blood cell count (min and max)
--  the presence of greater than 10% immature neutrophils (band forms)

DROP MATERIALIZED VIEW IF EXISTS SIRS_admit;
CREATE MATERIALIZED VIEW SIRS_admit AS
with bg as
(
  select bg.icustay_id
  , min(pco2) as PaCO2_Min
  from bg_admit bg
  group by bg.icustay_id
)
, labs as
(
  select
    pvt.icustay_id

    , min(case when label = 'BANDS' then valuenum else null end) as BANDS_min
    , max(case when label = 'BANDS' then valuenum else null end) as BANDS_max
    , min(case when label = 'WBC' then valuenum else null end) as WBC_min
    , max(case when label = 'WBC' then valuenum else null end) as WBC_max
  from
  ( -- begin query that extracts the data
    select ie.subject_id, ie.hadm_id, ie.icustay_id
    -- here we assign labels to ITEMIDs
    -- this also fuses together multiple ITEMIDs containing the same data
    , case
          when itemid = 51300 then 'WBC'
          when itemid = 51301 then 'WBC'
          when itemid = 51144 then 'BANDS'
        else null
      end as label
    , -- add in some sanity checks on the values
    -- the where clause below requires all valuenum to be > 0, so these are only upper limit checks
      case
        when itemid = 51300 and valuenum >  1000 then null -- 'WBC'
        when itemid = 51301 and valuenum >  1000 then null -- 'WBC'
        when itemid = 51144 and valuenum < 0 then null -- immature band forms, %
        when itemid = 51144 and valuenum > 100 then null -- immature band forms, %
      else le.valuenum
      end as valuenum

    from icustays ie

    left join labevents le
      on le.subject_id = ie.subject_id and le.hadm_id = ie.hadm_id
      and le.charttime between (ie.intime - interval '24' hour) and (ie.intime + interval '6' hour)
      and le.ITEMID in
      (
        -- comment is: LABEL | CATEGORY | FLUID | NUMBER OF ROWS IN LABEVENTS
        51144, -- BANDS - hematology
        51301, -- WHITE BLOOD CELLS | HEMATOLOGY | BLOOD | 753301
        51300  -- WBC COUNT | HEMATOLOGY | BLOOD | 2371
      )
      and valuenum is not null and valuenum > 0 -- lab values cannot be 0 and cannot be negative
  ) pvt
  group by pvt.icustay_id
)
-- VITAL SIGNS
, vitals as
(
  SELECT pvt.icustay_id

  -- Easier names
  , min(case when VitalID = 1 then valuenum else null end) as HeartRate_Min
  , max(case when VitalID = 1 then valuenum else null end) as HeartRate_Max
  , min(case when VitalID = 5 then valuenum else null end) as RespRate_Min
  , max(case when VitalID = 5 then valuenum else null end) as RespRate_Max
  , min(case when VitalID = 6 then valuenum else null end) as TempC_Min
  , max(case when VitalID = 6 then valuenum else null end) as TempC_Max

  FROM  (
    select ie.icustay_id
    , case
      when itemid in (211,220045) and valuenum > 0 and valuenum < 300 then 1 -- HeartRate
      when itemid in (615,618,220210,224690) and valuenum > 0 and valuenum < 70 then 5 -- RespRate
      when itemid in (223761,678) and valuenum > 70 and valuenum < 120  then 6 -- TempF, converted to degC in valuenum call
      when itemid in (223762,676) and valuenum > 10 and valuenum < 50  then 6 -- TempC
      else null end as VitalID

    -- convert F to C
    , case when itemid in (223761,678) then (valuenum-32)/1.8 else valuenum end as valuenum

    from icustays ie
    left join chartevents ce
      on ie.icustay_id = ce.icustay_id
      and ce.charttime
      between ie.intime - interval '6' hour
          and ie.intime + interval '6' hour
      -- exclude rows marked as error
      AND ce.error IS DISTINCT FROM 1
      and ce.itemid in
      (
      -- HEART RATE
      211, --"Heart Rate"
      220045, --"Heart Rate"


      -- RESPIRATORY RATE
      618,--	Respiratory Rate
      615,--	Resp Rate (Total)
      220210,--	Respiratory Rate
      224690, --	Respiratory Rate (Total)


      -- TEMPERATURE
      223762, -- "Temperature Celsius"
      676,	-- "Temperature C"
      223761, -- "Temperature Fahrenheit"
      678 --	"Temperature F"
      )
  ) pvt
  group by pvt.icustay_id
)
-- Aggregate the components for the score
, scorecomp as
(
select ie.icustay_id
  , v.Tempc_Min
  , v.Tempc_Max
  , v.HeartRate_Max
  , v.RespRate_Max
  , bg.PaCO2_Min
  , l.WBC_min
  , l.WBC_max
  , l.Bands_max

from icustays ie
left join bg
 on ie.icustay_id = bg.icustay_id
left join vitals v
  on ie.icustay_id = v.icustay_id
left join labs l
  on ie.icustay_id = l.icustay_id
)
, scorecalc as
(
  -- Calculate the final score
  -- note that if the underlying data is missing, the component is null
  -- eventually these are treated as 0 (normal), but knowing when data is missing is useful for debugging
  select icustay_id

  , case
      when Tempc_Min < 36.0 then 1
      when Tempc_Max > 38.0 then 1
      when Tempc_min is null then null
      else 0
    end as Temp_score

  , case
      when HeartRate_Max > 90.0  then 1
      when HeartRate_Max is null then null
      else 0
    end as HeartRate_score

  , case
      when RespRate_max > 20.0  then 1
      when PaCO2_Min < 32.0  then 1
      when coalesce(RespRate_max, PaCO2_Min) is null then null
      else 0
    end as Resp_score

  , case
      when WBC_Min <  4.0  then 1
      when WBC_Max > 12.0  then 1
      when Bands_max > 10 then 1-- > 10% immature neurophils (band forms)
      when coalesce(WBC_Min, Bands_max) is null then null
      else 0
    end as WBC_score

  from scorecomp
)
select
  ie.icustay_id
  -- Combine all the scores to get SIRS
  -- Impute 0 if the score is missing
  , coalesce(Temp_score,0)
  + coalesce(HeartRate_score,0)
  + coalesce(Resp_score,0)
  + coalesce(WBC_score,0)
    as SIRS
  , Temp_score, HeartRate_score, Resp_score, WBC_score
from icustays ie
left join scorecalc s
  on ie.icustay_id = s.icustay_id
order by ie.icustay_id;
