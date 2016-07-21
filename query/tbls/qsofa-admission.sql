-- ------------------------------------------------------------------
-- Title: Quick Sequential Organ Failure Assessment (qSOFA)
-- Originally written by: Alistair Johnson
-- Contact: aewj [at] mit [dot] edu
-- ------------------------------------------------------------------

-- This query extracts the quick sequential organ failure assessment on ADMISSION
-- It looks for the first values recorded for each of the 3 components
-- It also outputs the worst value in the first 6 hours, and the first set of concurrent measurements
-- This score was a recent revision of SOFA, aiming to detect patients at risk of sepsis.

-- Reference for qSOFA:
--    Singer M, et al. The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3)
--    Seymour CW, et al. Assessment of Clinical Criteria for Sepsis: For the Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3)

-- Variables used in qSOFA:
--  GCS, respiratory rate, systolic blood pressure

DROP MATERIALIZED VIEW IF EXISTS QSOFA_admit CASCADE;
CREATE MATERIALIZED VIEW QSOFA_admit AS

-- VITAL SIGNS
with vitals as
(
  SELECT pvt.icustay_id, pvt.charttime

  -- Easier names
  , (case when VitalID = 2 then valuenum else null end) as SysBP_Min
  , (case when VitalID = 5 then valuenum else null end) as RespRate_Max
  , ROW_NUMBER() over (partition by pvt.icustay_id, pvt.VitalID order by charttime) as rn

  FROM  (
    select ie.icustay_id, charttime
    , case
      when itemid in (51,442,455,6701,220179,220050) and valuenum > 0 and valuenum < 400 then 2 -- SysBP
      when itemid in (615,618,220210,224690) and valuenum > 0 and valuenum < 70 then 5 -- RespRate
      else null end as VitalID
        -- convert F to C
    , valuenum

    from icustays ie
    left join chartevents ce
      on ie.icustay_id = ce.icustay_id
      and ce.charttime
      between ie.intime - interval '6' hour
          and ie.intime + interval '6' hour
      and ce.itemid in
      (
      -- Systolic/diastolic
      51, --	Arterial BP [Systolic]
      442, --	Manual BP [Systolic]
      455, --	NBP [Systolic]
      6701, --	Arterial BP #2 [Systolic]
      220179, --	Non Invasive Blood Pressure systolic
      220050, --	Arterial Blood Pressure systolic

      -- RESPIRATORY RATE
      618,--	Respiratory Rate
      615,--	Resp Rate (Total)
      220210,--	Respiratory Rate
      224690 --	Respiratory Rate (Total)
      )
  ) pvt
)
-- GCS
, base as
(
  SELECT pvt.ICUSTAY_ID
  , pvt.charttime

  -- Easier names - note we coalesced Metavision and CareVue IDs below
  , max(case when pvt.itemid = 454 then pvt.valuenum else null end) as GCSMotor
  , max(case when pvt.itemid = 723 then pvt.valuenum else null end) as GCSVerbal
  , max(case when pvt.itemid = 184 then pvt.valuenum else null end) as GCSEyes

  -- If verbal was set to 0 in the below select, then this is an intubated patient
  , case
      when max(case when pvt.itemid = 723 then pvt.valuenum else null end) = 0
    then 1
    else 0
    end as EndoTrachFlag

  , ROW_NUMBER ()
          OVER (PARTITION BY pvt.ICUSTAY_ID ORDER BY pvt.charttime ASC) as rn

  FROM  (
  select l.ICUSTAY_ID
  -- merge the ITEMIDs so that the pivot applies to both metavision/carevue data
  , case
      when l.ITEMID in (723,223900) then 723
      when l.ITEMID in (454,223901) then 454
      when l.ITEMID in (184,220739) then 184
      else l.ITEMID end
    as ITEMID

  -- convert the data into a number, reserving a value of 0 for ET/Trach
  , case
      -- endotrach/vent is assigned a value of 0, later parsed specially
      when l.ITEMID = 723 and l.VALUE = '1.0 ET/Trach' then 0 -- carevue
      when l.ITEMID = 223900 and l.VALUE = 'No Response-ETT' then 0 -- metavision

      else VALUENUM
      end
    as VALUENUM
  , l.CHARTTIME
  from icustays ie
  left join CHARTEVENTS l
    on l.icustay_id = ie.icustay_id
    -- Only get data for the first 6 hours
    and l.charttime
    between ie.intime - interval '6' hour
        and ie.intime + interval '6' hour
    -- Isolate the desired GCS variables
    and l.ITEMID in
    (
      -- 198 -- GCS
      -- GCS components, CareVue
      184, 454, 723
      -- GCS components, Metavision
      , 223900, 223901, 220739
    )
  ) pvt
  group by pvt.ICUSTAY_ID, pvt.charttime
)
, gcs as (
  -- note b.rn=1 gives us the first gcs value, kept here for use later
  select b.*
  , b2.GCSVerbal as GCSVerbalPrev
  , b2.GCSMotor as GCSMotorPrev
  , b2.GCSEyes as GCSEyesPrev
  -- Calculate GCS, factoring in special case when they are intubated and prev vals
  -- note that the coalesce are used to implement the following if:
  --  if current value exists, use it
  --  if previous value exists, use it
  --  otherwise, default to normal
  , case
      -- replace GCS during sedation with 15
      when b.GCSVerbal = 0
        then 15
      when b.GCSVerbal is null and b2.GCSVerbal = 0
        then 15
      -- if previously they were intub, but they aren't now, do not use previous GCS values
      when b2.GCSVerbal = 0
        then
            coalesce(b.GCSMotor,6)
          + coalesce(b.GCSVerbal,5)
          + coalesce(b.GCSEyes,4)
      -- otherwise, add up score normally, imputing previous value if none available at current time
      else
            coalesce(b.GCSMotor,coalesce(b2.GCSMotor,6))
          + coalesce(b.GCSVerbal,coalesce(b2.GCSVerbal,5))
          + coalesce(b.GCSEyes,coalesce(b2.GCSEyes,4))
      end as GCS

  from base b
  -- join to itself within 6 hours to get previous value
  left join base b2
    on b.ICUSTAY_ID = b2.ICUSTAY_ID
    and b.rn = b2.rn+1
    and b2.charttime > b.charttime - interval '6' hour
)
, scorecomp as
(
  select ie.icustay_id
    -- use the first value we record on admit (i.e. in first 6 hours)
    , min(case when v.rn = 1 then v.SysBP_Min else null end) as SysBP_Min
    , max(case when v.rn = 1 then v.RespRate_max else null end) as RespRate_max
    , min(case when gcs.rn = 1 then gcs.GCS else null end) as GCS_min

    -- use the worst value we record on admit
    , min(v.SysBP_Min) as SysBP_min_worst
    , max(v.RespRate_max) as RespRate_max_worst
    , min(gcs.GCS) as GCS_min_worst
    , max(case when ve.icustay_id is not null then 1 else 0 end) as vent
    , max(case when va.icustay_id is not null then 1 else 0 end) as vaso

  from icustays ie
  left join vitals v
    on ie.icustay_id = v.icustay_id
  left join gcs gcs
    on ie.icustay_id = gcs.icustay_id
  -- extend the starttime backward 6 hours
  -- thus, a patient is treated as ventilated if the vent started/ended at most 6 hours after admission
  -- this also lets us include patients ventilated before ICU admission
  left join ventdurations ve
    on ie.icustay_id = ve.icustay_id
    and ie.intime between ve.starttime - interval '6' hour and ve.endtime + interval '6' hour
  -- similarly, we look for vasopressor usage on admission
  left join vasodur va
    on ie.icustay_id = va.icustay_id
    and ie.intime between va.starttime - interval '6' hour and va.endtime + interval '6' hour
  group by ie.icustay_id
)
, scorecalc as
(
  -- Calculate the final score
  -- note that if the underlying data is missing, the component is null
  -- eventually these are treated as 0 (normal), but knowing when data is missing is useful for debugging
  select s.*
  -- qSOFA components factoring in ventilation/vasopressor usage
  , case
      when vaso = 1 then 1
      when SysBP_Min is null then null
      when SysBP_Min   <= 100 then 1
      else 0 end
    as SysBP_score
  , case
      when GCS_min is null then null
      when GCS_min   <= 13 then 1
      else 0 end
    as GCS_score
  , case
      when vent = 1 then 1
      when RespRate_max is null then null
      when RespRate_max   >= 22 then 1
      else 0 end
    as RespRate_score

    -- qSOFA components if we do not factor in ventilation/vasopressor usage
    , case
        when SysBP_Min is null then null
        when SysBP_Min   <= 100 then 1
        else 0 end
      as SysBP_score_norx
    , case
        when GCS_min is null then null
        when GCS_min   <= 13 then 1
        else 0 end
      as GCS_score_norx
    , case
        when RespRate_max is null then null
        when RespRate_max   >= 22 then 1
        else 0 end
      as RespRate_score_norx

    -- similar qSOFA using worst values
    , case
        when vaso = 1 then 1
        when SysBP_min_worst is null then null
        when SysBP_min_worst   <= 100 then 1
        else 0 end
      as SysBP_score_worst
    , case
        when GCS_min_worst is null then null
        when GCS_min_worst   <= 13 then 1
        else 0 end
      as GCS_score_worst
    , case
        when vent = 1 then 1
        when RespRate_max_worst is null then null
        when RespRate_max_worst   >= 22 then 1
        else 0 end
      as RespRate_score_worst
  from scorecomp s
)
select s.*
  , coalesce(SysBP_score,0)
    + coalesce(GCS_score,0)
    + coalesce(RespRate_score,0)
    as qSOFA
  , coalesce(SysBP_score_norx,0)
    + coalesce(GCS_score_norx,0)
    + coalesce(RespRate_score_norx,0)
    as qSOFA_no_rx
  , coalesce(SysBP_score_worst,0)
    + coalesce(GCS_score_worst,0)
    + coalesce(RespRate_score_worst,0)
    as qSOFA_worst
from scorecalc s
order by icustay_id;
