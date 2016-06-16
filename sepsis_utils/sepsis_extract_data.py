import sys
import os
import psycopg2
import pandas as pd
import numpy as np

# === also define queries for custom time spans === #
# "T" is the number of hours after ICU admission to include at a minimum

def get_scores_at_time(con, T=3):
    schema_name = "mimiciii"

    query_vd = """
    ventsettings as
    (
      select
        ce.icustay_id, charttime
        -- case statement determining whether it is an instance of mech vent
        , max(
          case
            when itemid is null or value is null then 0 -- can't have null values
            when itemid = 720 and value != 'Other/Remarks' THEN 1  -- VentTypeRecorded
            when itemid = 467 and value = 'Ventilator' THEN 1 -- O2 delivery device == ventilator
            when itemid = 648 and value = 'Intubated/trach' THEN 1 -- Speech = intubated
            when itemid in
              (
              445, 448, 449, 450, 1340, 1486, 1600, 224687 -- minute volume
              , 639, 654, 681, 682, 683, 684,224685,224684,224686 -- tidal volume
              , 218,436,535,444,459,224697,224695,224696,224746,224747 -- High/Low/Peak/Mean/Neg insp force ("RespPressure")
              , 221,1,1211,1655,2000,226873,224738,224419,224750,227187 -- Insp pressure
              , 543 -- PlateauPressure
              , 5865,5866,224707,224709,224705,224706 -- APRV pressure
              , 60,437,505,506,686,220339,224700 -- PEEP
              , 3459 -- high pressure relief
              , 501,502,503,224702 -- PCV
              , 223,667,668,669,670,671,672 -- TCPCV
              , 157,158,1852,3398,3399,3400,3401,3402,3403,3404,8382,227809,227810 -- ETT
              , 224701 -- PSVlevel
              )
              THEN 1
            else 0
          end
          ) as MechVent
          , max(
            case when itemid is null or value is null then 0
              when itemid = 640 and value = 'Extubated' then 1
              when itemid = 640 and value = 'Self Extubation' then 1
            else 0
            end
            )
            as Extubated
          , max(
            case when itemid is null or value is null then 0
              when itemid = 640 and value = 'Self Extubation' then 1
            else 0
            end
            )
            as SelfExtubated

      from mimiciii.chartevents ce
      where value is not null
      and itemid in
      (
          640 -- extubated
          , 648 -- speech
          , 720 -- vent type
          , 467 -- O2 delivery device
          , 445, 448, 449, 450, 1340, 1486, 1600, 224687 -- minute volume
          , 639, 654, 681, 682, 683, 684,224685,224684,224686 -- tidal volume
          , 218,436,535,444,459,224697,224695,224696,224746,224747 -- High/Low/Peak/Mean/Neg insp force ("RespPressure")
          , 221,1,1211,1655,2000,226873,224738,224419,224750,227187 -- Insp pressure
          , 543 -- PlateauPressure
          , 5865,5866,224707,224709,224705,224706 -- APRV pressure
          , 60,437,505,506,686,220339,224700 -- PEEP
          , 3459 -- high pressure relief
          , 501,502,503,224702 -- PCV
          , 223,667,668,669,670,671,672 -- TCPCV
          , 157,158,1852,3398,3399,3400,3401,3402,3403,3404,8382,227809,227810 -- ETT
          , 224701 -- PSVlevel
      )
      group by icustay_id, charttime
    )
    -- now we convert CHARTTIME of ventilator settings into durations
    , vd1 as
    (
    select
        icustay_id
        -- this carries over the previous charttime which had a mechanical ventilation event
        , case
            when MechVent=1 then
              LAG(CHARTTIME, 1) OVER (partition by icustay_id, MechVent order by charttime)
            else null
          end as charttime_lag
        , charttime
        , MechVent
        , Extubated
        , SelfExtubated

        -- if this is a mechanical ventilation event, we calculate the time since the last event
        , case
            -- if the current observation indicates mechanical ventilation is present
            when MechVent=1 then
            -- copy over the previous charttime where mechanical ventilation was present
              CHARTTIME - (LAG(CHARTTIME, 1) OVER (partition by icustay_id, MechVent order by charttime))
            else null
          end as ventduration

        -- now we determine if the current mech vent event is a "new", i.e. they've just been intubated
        , case
          -- if there is an extubation flag, we mark any subsequent ventilation as a new ventilation event
            when Extubated = 1 then 0 -- extubation is *not* a new ventilation event, the *subsequent* row is
            when
              LAG(Extubated,1)
              OVER
              (
              partition by icustay_id, case when MechVent=1 or Extubated=1 then 1 else 0 end
              order by charttime
              )
              = 1 then 1
              -- if there is less than 8 hours between vent settings, we do not treat this as a new ventilation event
            when (CHARTTIME - (LAG(CHARTTIME, 1) OVER (partition by icustay_id, MechVent order by charttime))) <= interval '8' hour
              then 0
          else 1
          end as newvent
    FROM
      ventsettings
    )
    , vd2 as
    (
    select vd1.*
    -- create a cumulative sum of the instances of new ventilation
    -- this results in a monotonic integer assigned to each instance of ventilation
    , case when MechVent=1 or Extubated = 1 then
        SUM( newvent )
        OVER ( partition by icustay_id order by charttime )
      else null end
      as ventnum
    from vd1
    -- now we can isolate to just rows with ventilation settings/extubation settings
    -- (before we had rows with extubation flags)
    -- this removes any null values for newvent
    where
      MechVent = 1 or Extubated = 1
    )
    , vd as
    (
    -- finally, create the durations for each mechanical ventilation instance
    select icustay_id, ventnum
      , min(charttime) as starttime
      , max(charttime) as endtime
    from vd2
    group by icustay_id, ventnum
    order by icustay_id, ventnum
    )
    """

    query_bgart = """
    bg_stg1 as
    (
    select
        pvt.SUBJECT_ID, pvt.HADM_ID, pvt.ICUSTAY_ID, pvt.CHARTTIME
        , max(case when label = 'SPECIMEN' then value else null end) as SPECIMEN
        , max(case when label = 'AADO2' then valuenum else null end) as AADO2
        , max(case when label = 'BASEEXCESS' then valuenum else null end) as BASEEXCESS
        , max(case when label = 'BICARBONATE' then valuenum else null end) as BICARBONATE
        , max(case when label = 'TOTALCO2' then valuenum else null end) as TOTALCO2
        , max(case when label = 'CARBOXYHEMOGLOBIN' then valuenum else null end) as CARBOXYHEMOGLOBIN
        , max(case when label = 'CHLORIDE' then valuenum else null end) as CHLORIDE
        , max(case when label = 'CALCIUM' then valuenum else null end) as CALCIUM
        , max(case when label = 'GLUCOSE' then valuenum else null end) as GLUCOSE
        , max(case when label = 'HEMATOCRIT' then valuenum else null end) as HEMATOCRIT
        , max(case when label = 'HEMOGLOBIN' then valuenum else null end) as HEMOGLOBIN
        , max(case when label = 'INTUBATED' then valuenum else null end) as INTUBATED
        , max(case when label = 'LACTATE' then valuenum else null end) as LACTATE
        , max(case when label = 'METHEMOGLOBIN' then valuenum else null end) as METHEMOGLOBIN
        , max(case when label = 'O2FLOW' then valuenum else null end) as O2FLOW
        , max(case when label = 'FIO2' then valuenum else null end) as FIO2
        , max(case when label = 'SO2' then valuenum else null end) as SO2 -- OXYGENSATURATION
        , max(case when label = 'PCO2' then valuenum else null end) as PCO2
        , max(case when label = 'PEEP' then valuenum else null end) as PEEP
        , max(case when label = 'PH' then valuenum else null end) as PH
        , max(case when label = 'PO2' then valuenum else null end) as PO2
        , max(case when label = 'POTASSIUM' then valuenum else null end) as POTASSIUM
        , max(case when label = 'REQUIREDO2' then valuenum else null end) as REQUIREDO2
        , max(case when label = 'SODIUM' then valuenum else null end) as SODIUM
        , max(case when label = 'TEMPERATURE' then valuenum else null end) as TEMPERATURE
        , max(case when label = 'TIDALVOLUME' then valuenum else null end) as TIDALVOLUME
        , max(case when label = 'VENTILATIONRATE' then valuenum else null end) as VENTILATIONRATE
        , max(case when label = 'VENTILATOR' then valuenum else null end) as VENTILATOR
        from
        ( -- begin query that extracts the data
          select ie.subject_id, ie.hadm_id, ie.icustay_id
          -- here we assign labels to ITEMIDs
          -- this also fuses together multiple ITEMIDs containing the same data
              , case
                when itemid = 50800 then 'SPECIMEN'
                when itemid = 50801 then 'AADO2'
                when itemid = 50802 then 'BASEEXCESS'
                when itemid = 50803 then 'BICARBONATE'
                when itemid = 50804 then 'TOTALCO2'
                when itemid = 50805 then 'CARBOXYHEMOGLOBIN'
                when itemid = 50806 then 'CHLORIDE'
                when itemid = 50808 then 'CALCIUM'
                when itemid = 50809 then 'GLUCOSE'
                when itemid = 50810 then 'HEMATOCRIT'
                when itemid = 50811 then 'HEMOGLOBIN'
                when itemid = 50812 then 'INTUBATED'
                when itemid = 50813 then 'LACTATE'
                when itemid = 50814 then 'METHEMOGLOBIN'
                when itemid = 50815 then 'O2FLOW'
                when itemid = 50816 then 'FIO2'
                when itemid = 50817 then 'SO2' -- OXYGENSATURATION
                when itemid = 50818 then 'PCO2'
                when itemid = 50819 then 'PEEP'
                when itemid = 50820 then 'PH'
                when itemid = 50821 then 'PO2'
                when itemid = 50822 then 'POTASSIUM'
                when itemid = 50823 then 'REQUIREDO2'
                when itemid = 50824 then 'SODIUM'
                when itemid = 50825 then 'TEMPERATURE'
                when itemid = 50826 then 'TIDALVOLUME'
                when itemid = 50827 then 'VENTILATIONRATE'
                when itemid = 50828 then 'VENTILATOR'
                else null
                end as label
                , charttime
                , value
                -- add in some sanity checks on the values
                , case
                  when valuenum <= 0 then null
                  when itemid = 50810 and valuenum > 100 then null -- hematocrit
                  when itemid = 50816 and valuenum > 100 then null -- FiO2
                  when itemid = 50817 and valuenum > 100 then null -- O2 sat
                  when itemid = 50815 and valuenum >  70 then null -- O2 flow
                  when itemid = 50821 and valuenum > 800 then null -- PO2
                   -- conservative upper limit
                else valuenum
                end as valuenum
            from mimiciii.icustays ie
            inner join times tt
                on ie.icustay_id = tt.icustay_id
            left join mimiciii.labevents le
              on le.subject_id = ie.subject_id and le.hadm_id = ie.hadm_id
              and le.charttime between tt.starttime - interval '12' hour and tt.endtime
              and le.ITEMID in
              -- blood gases
              (
                50800, 50801, 50802, 50803, 50804, 50805, 50806, 50807, 50808, 50809
                , 50810, 50811, 50812, 50813, 50814, 50815, 50816, 50817, 50818, 50819
                , 50820, 50821, 50822, 50823, 50824, 50825, 50826, 50827, 50828
                , 51545
              )
        ) pvt
        group by pvt.subject_id, pvt.hadm_id, pvt.icustay_id, pvt.CHARTTIME
        order by pvt.subject_id, pvt.hadm_id, pvt.icustay_id, pvt.CHARTTIME
    )
    , stg_spo2 as
    (
      select SUBJECT_ID, HADM_ID, ce.ICUSTAY_ID, CHARTTIME
        -- max here is just used to group SpO2 by charttime
        , max(case when valuenum <= 0 or valuenum > 100 then null else valuenum end) as SpO2
      from CHARTEVENTS ce
      inner join times tt
          on ce.icustay_id = tt.icustay_id
      -- o2 sat
      where ITEMID in
      (
        646 -- SpO2
      , 220277 -- O2 saturation pulseoxymetry
      )
      group by SUBJECT_ID, HADM_ID, ce.ICUSTAY_ID, CHARTTIME
    )
    , stg_fio2 as
    (
      select SUBJECT_ID, HADM_ID, ce.ICUSTAY_ID, CHARTTIME
        -- pre-process the FiO2s to ensure they are between 21-100%
        , max(
            case
              when itemid = 223835
                then case
                  when valuenum > 0 and valuenum <= 1
                    then valuenum * 100
                  -- improperly input data - looks like O2 flow in litres
                  when valuenum > 1 and valuenum < 21
                    then null
                  when valuenum >= 21 and valuenum <= 100
                    then valuenum
                  else null end -- unphysiological
            when itemid in (3420, 3422)
            -- all these values are well formatted
                then valuenum
            when itemid = 190 and valuenum > 0.20 and valuenum < 1
            -- well formatted but not in %
                then valuenum * 100
          else null end
        ) as fio2_chartevents
      from CHARTEVENTS ce
      inner join times tt
          on ce.icustay_id = tt.icustay_id
      where ITEMID in
      (
        3420 -- FiO2
      , 190 -- FiO2 set
      , 223835 -- Inspired O2 Fraction (FiO2)
      , 3422 -- FiO2 [measured]
      )
      group by SUBJECT_ID, HADM_ID, ce.ICUSTAY_ID, CHARTTIME
    )
    , bg_stg2 as
    (
        select bg.*
          , ROW_NUMBER() OVER (partition by bg.icustay_id, bg.charttime order by s1.charttime DESC) as lastRowSpO2
          , s1.spo2
        from bg_stg1 bg
        left join stg_spo2 s1
          -- same patient
          on  bg.icustay_id = s1.icustay_id
          -- spo2 occurred at most 2 hours before this blood gas
          and s1.charttime between bg.charttime - interval '2' hour and bg.charttime
        where bg.po2 is not null
    )
    , bg_stg3 as
    (
        select bg.*
          , ROW_NUMBER() OVER (partition by bg.icustay_id, bg.charttime order by s2.charttime DESC) as lastRowFiO2
          , s2.fio2_chartevents

          -- create our specimen prediction
          ,  1/(1+exp(-(-0.02544
          +    0.04598 * po2
          + coalesce(-0.15356 * spo2             , -0.15356 *   97.49420 +    0.13429)
          + coalesce( 0.00621 * fio2_chartevents ,  0.00621 *   51.49550 +   -0.24958)
          + coalesce( 0.10559 * hemoglobin       ,  0.10559 *   10.32307 +    0.05954)
          + coalesce( 0.13251 * so2              ,  0.13251 *   93.66539 +   -0.23172)
          + coalesce(-0.01511 * pco2             , -0.01511 *   42.08866 +   -0.01630)
          + coalesce( 0.01480 * fio2             ,  0.01480 *   63.97836 +   -0.31142)
          + coalesce(-0.00200 * aado2            , -0.00200 *  442.21186 +   -0.01328)
          + coalesce(-0.03220 * bicarbonate      , -0.03220 *   22.96894 +   -0.06535)
          + coalesce( 0.05384 * totalco2         ,  0.05384 *   24.72632 +   -0.01405)
          + coalesce( 0.08202 * lactate          ,  0.08202 *    3.06436 +    0.06038)
          + coalesce( 0.10956 * ph               ,  0.10956 *    7.36233 +   -0.00617)
          + coalesce( 0.00848 * o2flow           ,  0.00848 *    7.59362 +   -0.35803)
          ))) as SPECIMEN_PROB
        from bg_stg2 bg
        left join stg_fio2 s2
          -- same patient
          on  bg.icustay_id = s2.icustay_id
          -- fio2 occurred at most 4 hours before this blood gas
          and s2.charttime between bg.charttime - interval '4' hour and bg.charttime
        where bg.lastRowSpO2 = 1 -- only the row with the most recent SpO2 (if no SpO2 found lastRowSpO2 = 1)
    )
    , bgart as
    (
        select subject_id, hadm_id,
        icustay_id, charttime
        , SPECIMEN -- raw data indicating sample type, only present 80% of the time

        -- prediction of specimen for missing data
        , case
              when SPECIMEN is not null then SPECIMEN
              when SPECIMEN_PROB > 0.75 then 'ART'
            else null end as SPECIMEN_PRED
        , SPECIMEN_PROB

        -- oxygen related parameters
        , SO2, spo2 -- note spo2 is from chartevents
        , PO2, PCO2
        , fio2_chartevents, FIO2
        , AADO2
        -- also calculate AADO2
        , case
            when  PO2 is not null
              and pco2 is not null
              and coalesce(FIO2, fio2_chartevents) is not null
             -- multiple by 100 because FiO2 is in a % but should be a fraction
              then (coalesce(FIO2, fio2_chartevents)/100) * (760 - 47) - (pco2/0.8) - po2
            else null
          end as AADO2_calc
        , case
            when PO2 is not null and coalesce(FIO2, fio2_chartevents) is not null
             -- multiply by 100 because FiO2 is in a % but should be a fraction
              then 100*PO2/(coalesce(FIO2, fio2_chartevents))
            else null
          end as PaO2FiO2
        -- acid-base parameters
        , PH, BASEEXCESS
        , BICARBONATE, TOTALCO2

        -- blood count parameters
        , HEMATOCRIT
        , HEMOGLOBIN
        , CARBOXYHEMOGLOBIN
        , METHEMOGLOBIN

        -- chemistry
        , CHLORIDE, CALCIUM
        , TEMPERATURE
        , POTASSIUM, SODIUM
        , LACTATE
        , GLUCOSE

        -- ventilation stuff that's sometimes input
        , INTUBATED, TIDALVOLUME, VENTILATIONRATE, VENTILATOR
        , PEEP, O2Flow
        , REQUIREDO2
        from bg_stg3
        where lastRowFiO2 = 1 -- only the most recent FiO2
        -- restrict it to *only* arterial samples
        and (SPECIMEN = 'ART' or SPECIMEN_PROB > 0.75)
    )
    """

    query_labs = """
    labs as (
    select
      pvt.subject_id, pvt.hadm_id, pvt.icustay_id
      , min(case when label = 'ANION GAP' then valuenum else null end) as ANIONGAP_min
      , max(case when label = 'ANION GAP' then valuenum else null end) as ANIONGAP_max
      , min(case when label = 'ALBUMIN' then valuenum else null end) as ALBUMIN_min
      , max(case when label = 'ALBUMIN' then valuenum else null end) as ALBUMIN_max
      , min(case when label = 'BANDS' then valuenum else null end) as BANDS_min
      , max(case when label = 'BANDS' then valuenum else null end) as BANDS_max
      , min(case when label = 'BICARBONATE' then valuenum else null end) as BICARBONATE_min
      , max(case when label = 'BICARBONATE' then valuenum else null end) as BICARBONATE_max
      , min(case when label = 'BILIRUBIN' then valuenum else null end) as BILIRUBIN_min
      , max(case when label = 'BILIRUBIN' then valuenum else null end) as BILIRUBIN_max
      , min(case when label = 'CREATININE' then valuenum else null end) as CREATININE_min
      , max(case when label = 'CREATININE' then valuenum else null end) as CREATININE_max
      , min(case when label = 'CHLORIDE' then valuenum else null end) as CHLORIDE_min
      , max(case when label = 'CHLORIDE' then valuenum else null end) as CHLORIDE_max
      , min(case when label = 'GLUCOSE' then valuenum else null end) as GLUCOSE_min
      , max(case when label = 'GLUCOSE' then valuenum else null end) as GLUCOSE_max
      , min(case when label = 'HEMATOCRIT' then valuenum else null end) as HEMATOCRIT_min
      , max(case when label = 'HEMATOCRIT' then valuenum else null end) as HEMATOCRIT_max
      , min(case when label = 'HEMOGLOBIN' then valuenum else null end) as HEMOGLOBIN_min
      , max(case when label = 'HEMOGLOBIN' then valuenum else null end) as HEMOGLOBIN_max
      , min(case when label = 'LACTATE' then valuenum else null end) as LACTATE_min
      , max(case when label = 'LACTATE' then valuenum else null end) as LACTATE_max
      , min(case when label = 'PLATELET' then valuenum else null end) as PLATELET_min
      , max(case when label = 'PLATELET' then valuenum else null end) as PLATELET_max
      , min(case when label = 'POTASSIUM' then valuenum else null end) as POTASSIUM_min
      , max(case when label = 'POTASSIUM' then valuenum else null end) as POTASSIUM_max
      , min(case when label = 'PTT' then valuenum else null end) as PTT_min
      , max(case when label = 'PTT' then valuenum else null end) as PTT_max
      , min(case when label = 'INR' then valuenum else null end) as INR_min
      , max(case when label = 'INR' then valuenum else null end) as INR_max
      , min(case when label = 'PT' then valuenum else null end) as PT_min
      , max(case when label = 'PT' then valuenum else null end) as PT_max
      , min(case when label = 'SODIUM' then valuenum else null end) as SODIUM_min
      , max(case when label = 'SODIUM' then valuenum else null end) as SODIUM_max
      , min(case when label = 'BUN' then valuenum else null end) as BUN_min
      , max(case when label = 'BUN' then valuenum else null end) as BUN_max
      , min(case when label = 'WBC' then valuenum else null end) as WBC_min
      , max(case when label = 'WBC' then valuenum else null end) as WBC_max


    from
    ( -- begin query that extracts the data
      select ie.subject_id, ie.hadm_id, ie.icustay_id
      -- here we assign labels to ITEMIDs
      -- this also fuses together multiple ITEMIDs containing the same data
      , case
            when itemid = 50868 then 'ANION GAP'
            when itemid = 50862 then 'ALBUMIN'
            when itemid = 50882 then 'BICARBONATE'
            when itemid = 50885 then 'BILIRUBIN'
            when itemid = 50912 then 'CREATININE'
            when itemid = 50806 then 'CHLORIDE'
            when itemid = 50902 then 'CHLORIDE'
            when itemid = 50809 then 'GLUCOSE'
            when itemid = 50931 then 'GLUCOSE'
            when itemid = 50810 then 'HEMATOCRIT'
            when itemid = 51221 then 'HEMATOCRIT'
            when itemid = 50811 then 'HEMOGLOBIN'
            when itemid = 51222 then 'HEMOGLOBIN'
            when itemid = 50813 then 'LACTATE'
            when itemid = 51265 then 'PLATELET'
            when itemid = 50822 then 'POTASSIUM'
            when itemid = 50971 then 'POTASSIUM'
            when itemid = 51275 then 'PTT'
            when itemid = 51237 then 'INR'
            when itemid = 51274 then 'PT'
            when itemid = 50824 then 'SODIUM'
            when itemid = 50983 then 'SODIUM'
            when itemid = 51006 then 'BUN'
            when itemid = 51300 then 'WBC'
            when itemid = 51301 then 'WBC'
            when itemid = 51144 then 'BANDS'
          else null
        end as label
      , -- add in some sanity checks on the values
      -- the where clause below requires all valuenum to be > 0, so these are only upper limit checks
        case
          when itemid = 50862 and valuenum >    10 then null -- g/dL 'ALBUMIN'
          when itemid = 50868 and valuenum > 10000 then null -- mEq/L 'ANION GAP'
          when itemid = 50882 and valuenum > 10000 then null -- mEq/L 'BICARBONATE'
          when itemid = 50885 and valuenum >   150 then null -- mg/dL 'BILIRUBIN'
          when itemid = 50806 and valuenum > 10000 then null -- mEq/L 'CHLORIDE'
          when itemid = 50902 and valuenum > 10000 then null -- mEq/L 'CHLORIDE'
          when itemid = 50912 and valuenum >   150 then null -- mg/dL 'CREATININE'
          when itemid = 50809 and valuenum > 10000 then null -- mg/dL 'GLUCOSE'
          when itemid = 50931 and valuenum > 10000 then null -- mg/dL 'GLUCOSE'
          when itemid = 50810 and valuenum >   100 then null -- % 'HEMATOCRIT'
          when itemid = 51221 and valuenum >   100 then null -- % 'HEMATOCRIT'
          when itemid = 50811 and valuenum >    50 then null -- g/dL 'HEMOGLOBIN'
          when itemid = 51222 and valuenum >    50 then null -- g/dL 'HEMOGLOBIN'
          when itemid = 50813 and valuenum >    50 then null -- mmol/L 'LACTATE'
          when itemid = 51265 and valuenum > 10000 then null -- K/uL 'PLATELET'
          when itemid = 50822 and valuenum >    30 then null -- mEq/L 'POTASSIUM'
          when itemid = 50971 and valuenum >    30 then null -- mEq/L 'POTASSIUM'
          when itemid = 51275 and valuenum >   150 then null -- sec 'PTT'
          when itemid = 51237 and valuenum >    50 then null -- 'INR'
          when itemid = 51274 and valuenum >   150 then null -- sec 'PT'
          when itemid = 50824 and valuenum >   200 then null -- mEq/L == mmol/L 'SODIUM'
          when itemid = 50983 and valuenum >   200 then null -- mEq/L == mmol/L 'SODIUM'
          when itemid = 51006 and valuenum >   300 then null -- 'BUN'
          when itemid = 51300 and valuenum >  1000 then null -- 'WBC'
          when itemid = 51301 and valuenum >  1000 then null -- 'WBC'
          when itemid = 51144 and valuenum < 0 then null -- immature band forms, %
          when itemid = 51144 and valuenum > 100 then null -- immature band forms, %
        else le.valuenum
        end as valuenum

      from mimiciii.icustays ie
      inner join times tt
        on ie.icustay_id = tt.icustay_id
      left join mimiciii.labevents le
        on le.subject_id = ie.subject_id and le.hadm_id = ie.hadm_id
        and le.charttime between tt.starttime - interval '12' hour and tt.endtime
        and le.ITEMID in
        (
          -- comment is: LABEL | CATEGORY | FLUID | NUMBER OF ROWS IN LABEVENTS
          50868, -- ANION GAP | CHEMISTRY | BLOOD | 769895
          50862, -- ALBUMIN | CHEMISTRY | BLOOD | 146697
          51144, -- BANDS - hematology
          50882, -- BICARBONATE | CHEMISTRY | BLOOD | 780733
          50885, -- BILIRUBIN, TOTAL | CHEMISTRY | BLOOD | 238277
          50912, -- CREATININE | CHEMISTRY | BLOOD | 797476
          50902, -- CHLORIDE | CHEMISTRY | BLOOD | 795568
          50806, -- CHLORIDE, WHOLE BLOOD | BLOOD GAS | BLOOD | 48187
          50931, -- GLUCOSE | CHEMISTRY | BLOOD | 748981
          50809, -- GLUCOSE | BLOOD GAS | BLOOD | 196734
          51221, -- HEMATOCRIT | HEMATOLOGY | BLOOD | 881846
          50810, -- HEMATOCRIT, CALCULATED | BLOOD GAS | BLOOD | 89715
          51222, -- HEMOGLOBIN | HEMATOLOGY | BLOOD | 752523
          50811, -- HEMOGLOBIN | BLOOD GAS | BLOOD | 89712
          50813, -- LACTATE | BLOOD GAS | BLOOD | 187124
          51265, -- PLATELET COUNT | HEMATOLOGY | BLOOD | 778444
          50971, -- POTASSIUM | CHEMISTRY | BLOOD | 845825
          50822, -- POTASSIUM, WHOLE BLOOD | BLOOD GAS | BLOOD | 192946
          51275, -- PTT | HEMATOLOGY | BLOOD | 474937
          51237, -- INR(PT) | HEMATOLOGY | BLOOD | 471183
          51274, -- PT | HEMATOLOGY | BLOOD | 469090
          50983, -- SODIUM | CHEMISTRY | BLOOD | 808489
          50824, -- SODIUM, WHOLE BLOOD | BLOOD GAS | BLOOD | 71503
          51006, -- UREA NITROGEN | CHEMISTRY | BLOOD | 791925
          51301, -- WHITE BLOOD CELLS | HEMATOLOGY | BLOOD | 753301
          51300  -- WBC COUNT | HEMATOLOGY | BLOOD | 2371
        )
        and valuenum is not null and valuenum > 0 -- lab values cannot be 0 and cannot be negative
    ) pvt
    group by pvt.subject_id, pvt.hadm_id, pvt.icustay_id
    order by pvt.subject_id, pvt.hadm_id, pvt.icustay_id
    )
    """

    query_gcs = """
    gcs_stg0 as
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
      from mimiciii.CHARTEVENTS l
      -- get intime for charttime subselection
      inner join mimiciii.icustays b
        on l.icustay_id = b.icustay_id
    inner join times tt
            on l.icustay_id = tt.icustay_id

      -- Isolate the desired GCS variables
      where l.ITEMID in
      (
        -- 198 -- GCS
        -- GCS components, CareVue
        184, 454, 723
        -- GCS components, Metavision
        , 223900, 223901, 220739
      )
      and l.charttime between b.intime and tt.endtime
      ) pvt
      group by pvt.ICUSTAY_ID, pvt.charttime
    )
    , gcs_stg1 as (
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

      from gcs_stg0 b
      -- join to itself within 6 hours to get previous value
      left join gcs_stg0 b2
        on b.ICUSTAY_ID = b2.ICUSTAY_ID and b.rn = b2.rn+1 and b2.charttime > b.charttime - interval '6' hour
    )
    , gcs_final as (
      select gcs.*
      -- This sorts the data by GCS, so rn=1 is the the lowest GCS values to keep
      , ROW_NUMBER ()
              OVER (PARTITION BY gcs.ICUSTAY_ID
                    ORDER BY gcs.GCS
                   ) as IsMinGCS
      from gcs_stg1 gcs
    )
    , gcs as
    (
        select ie.SUBJECT_ID, ie.HADM_ID, ie.ICUSTAY_ID
        -- The minimum GCS is determined by the above row partition, we only join if IsMinGCS=1
        , GCS as MinGCS
        , coalesce(GCSMotor,GCSMotorPrev) as GCSMotor
        , coalesce(GCSVerbal,GCSVerbalPrev) as GCSVerbal
        , coalesce(GCSEyes,GCSEyesPrev) as GCSEyes
        , EndoTrachFlag as EndoTrachFlag

        -- subselect down to the cohort of eligible patients
        from mimiciii.icustays ie
        left join gcs_final gs
          on ie.ICUSTAY_ID = gs.ICUSTAY_ID and gs.IsMinGCS = 1
        ORDER BY ie.ICUSTAY_ID
    )
    """

    query_vitals = """
    vitals as
    (
        SELECT pvt.subject_id, pvt.hadm_id, pvt.icustay_id

        -- Easier names
        , min(case when VitalID = 1 then valuenum else null end) as HeartRate_Min
        , max(case when VitalID = 1 then valuenum else null end) as HeartRate_Max
        , min(case when VitalID = 2 then valuenum else null end) as SysBP_Min
        , max(case when VitalID = 2 then valuenum else null end) as SysBP_Max
        , min(case when VitalID = 3 then valuenum else null end) as DiasBP_Min
        , max(case when VitalID = 3 then valuenum else null end) as DiasBP_Max
        , min(case when VitalID = 4 then valuenum else null end) as MeanBP_Min
        , max(case when VitalID = 4 then valuenum else null end) as MeanBP_Max
        , min(case when VitalID = 5 then valuenum else null end) as RespRate_Min
        , max(case when VitalID = 5 then valuenum else null end) as RespRate_Max
        , min(case when VitalID = 6 then valuenum else null end) as TempC_Min
        , max(case when VitalID = 6 then valuenum else null end) as TempC_Max
        , min(case when VitalID = 7 then valuenum else null end) as SpO2_Min
        , max(case when VitalID = 7 then valuenum else null end) as SpO2_Max
        , min(case when VitalID = 8 then valuenum else null end) as Glucose_Min
        , max(case when VitalID = 8 then valuenum else null end) as Glucose_Max

        FROM  (
          select ie.subject_id, ie.hadm_id, ie.icustay_id
          , case
            when itemid in (211,220045) and valuenum > 0 and valuenum < 300 then 1 -- HeartRate
            when itemid in (51,442,455,6701,220179,220050) and valuenum > 0 and valuenum < 400 then 2 -- SysBP
            when itemid in (8368,8440,8441,8555,220180,220051) and valuenum > 0 and valuenum < 300 then 3 -- DiasBP
            when itemid in (456,52,6702,443,220052,220181,225312) and valuenum > 0 and valuenum < 300 then 4 -- MeanBP
            when itemid in (615,618,220210,224690) and valuenum > 0 and valuenum < 70 then 5 -- RespRate
            when itemid in (223761,678) and valuenum > 70 and valuenum < 120  then 6 -- TempF, converted to degC in valuenum call
            when itemid in (223762,676) and valuenum > 10 and valuenum < 50  then 6 -- TempC
            when itemid in (646,220277) and valuenum > 0 and valuenum <= 100 then 7 -- SpO2
            when itemid in (807,811,1529,3745,3744,225664,220621,226537) and valuenum > 0 then 8 -- Glucose

            else null end as VitalID
              -- convert F to C
          , case when itemid in (223761,678) then (valuenum-32)/1.8 else valuenum end as valuenum

          from mimiciii.icustays ie
          inner join times tt
              on ie.icustay_id = tt.icustay_id
          left join mimiciii.chartevents ce
          on ie.subject_id = ce.subject_id and ie.hadm_id = ce.hadm_id and ie.icustay_id = ce.icustay_id
          and ce.charttime between ie.intime and tt.endtime
          where ce.itemid in
          (
          -- HEART RATE
          211, --"Heart Rate"
          220045, --"Heart Rate"

          -- Systolic/diastolic

          51, --    Arterial BP [Systolic]
          442, --    Manual BP [Systolic]
          455, --    NBP [Systolic]
          6701, --    Arterial BP #2 [Systolic]
          220179, --    Non Invasive Blood Pressure systolic
          220050, --    Arterial Blood Pressure systolic

          8368, --    Arterial BP [Diastolic]
          8440, --    Manual BP [Diastolic]
          8441, --    NBP [Diastolic]
          8555, --    Arterial BP #2 [Diastolic]
          220180, --    Non Invasive Blood Pressure diastolic
          220051, --    Arterial Blood Pressure diastolic


          -- MEAN ARTERIAL PRESSURE
          456, --"NBP Mean"
          52, --"Arterial BP Mean"
          6702, --    Arterial BP Mean #2
          443, --    Manual BP Mean(calc)
          220052, --"Arterial Blood Pressure mean"
          220181, --"Non Invasive Blood Pressure mean"
          225312, --"ART BP mean"

          -- RESPIRATORY RATE
          618,--    Respiratory Rate
          615,--    Resp Rate (Total)
          220210,--    Respiratory Rate
          224690, --    Respiratory Rate (Total)


          -- SPO2, peripheral
          646, 220277,

          -- GLUCOSE, both lab and fingerstick
          807,--    Fingerstick Glucose
          811,--    Glucose (70-105)
          1529,--    Glucose
          3745,--    BloodGlucose
          3744,--    Blood Glucose
          225664,--    Glucose finger stick
          220621,--    Glucose (serum)
          226537,--    Glucose (whole blood)

          -- TEMPERATURE
          223762, -- "Temperature Celsius"
          676,    -- "Temperature C"
          223761, -- "Temperature Fahrenheit"
          678 --    "Temperature F"
          )
        ) pvt
        group by pvt.subject_id, pvt.hadm_id, pvt.icustay_id
        order by pvt.subject_id, pvt.hadm_id, pvt.icustay_id
    )
    """

    query_vent = """
    vent as
    (
        select
            icustay_id, MechVent
        from
        (
          select
            ce.icustay_id
            -- case statement determining whether it is an instance of mech vent
            , max(
              case
                when itemid is null or value is null then 0 -- can't have null values
                when itemid = 720 and value != 'Other/Remarks' THEN 1  -- VentTypeRecorded
                when itemid = 467 and value = 'Ventilator' THEN 1 -- O2 delivery device == ventilator
                when itemid = 648 and value = 'Intubated/trach' THEN 1 -- Speech = intubated
                when itemid in
                  (
                  445, 448, 449, 450, 1340, 1486, 1600, 224687 -- minute volume
                  , 639, 654, 681, 682, 683, 684,224685,224684,224686 -- tidal volume
                  , 218,436,535,444,459,224697,224695,224696,224746,224747 -- High/Low/Peak/Mean/Neg insp force ("RespPressure")
                  , 221,1,1211,1655,2000,226873,224738,224419,224750,227187 -- Insp pressure
                  , 543 -- PlateauPressure
                  , 5865,5866,224707,224709,224705,224706 -- APRV pressure
                  , 60,437,505,506,686,220339,224700 -- PEEP
                  , 3459 -- high pressure relief
                  , 501,502,503,224702 -- PCV
                  , 223,667,668,669,670,671,672 -- TCPCV
                  , 157,158,1852,3398,3399,3400,3401,3402,3403,3404,8382,227809,227810 -- ETT
                  , 224701 -- PSVlevel
                  )
                  THEN 1
                else 0
              end
              ) as MechVent
              , max(
                case when itemid is null or value is null then 0
                  when itemid = 640 and value = 'Extubated' then 1
                  when itemid = 640 and value = 'Self Extubation' then 1
                else 0
                end
                )
                as Extubated
              , max(
                case when itemid is null or value is null then 0
                  when itemid = 640 and value = 'Self Extubation' then 1
                else 0
                end
                )
                as SelfExtubated

          from mimiciii.chartevents ce
          inner join icustays ie
            on ce.icustay_id = ie.icustay_id
          inner join times tt
            on ce.charttime between tt.starttime and tt.endtime
          where value is not null
          and itemid in
          (
              640 -- extubated
              , 648 -- speech
              , 720 -- vent type
              , 467 -- O2 delivery device
              , 445, 448, 449, 450, 1340, 1486, 1600, 224687 -- minute volume
              , 639, 654, 681, 682, 683, 684,224685,224684,224686 -- tidal volume
              , 218,436,535,444,459,224697,224695,224696,224746,224747 -- High/Low/Peak/Mean/Neg insp force ("RespPressure")
              , 221,1,1211,1655,2000,226873,224738,224419,224750,227187 -- Insp pressure
              , 543 -- PlateauPressure
              , 5865,5866,224707,224709,224705,224706 -- APRV pressure
              , 60,437,505,506,686,220339,224700 -- PEEP
              , 3459 -- high pressure relief
              , 501,502,503,224702 -- PCV
              , 223,667,668,669,670,671,672 -- TCPCV
              , 157,158,1852,3398,3399,3400,3401,3402,3403,3404,8382,227809,227810 -- ETT
              , 224701 -- PSVlevel
          )
          group by ce.icustay_id
         ) ventsettings
    )
    """

    query_uo = """
    uo as
    (
    select
      -- patient identifiers
      ie.subject_id, ie.hadm_id, ie.icustay_id

      -- volumes associated with urine output ITEMIDs
      , sum(VALUE) as UrineOutput

    from mimiciii.icustays ie
    inner join times tt
        on ie.icustay_id = tt.icustay_id
    -- Join to the outputevents table to get urine output
    left join mimiciii.outputevents oe
    -- join on all patient identifiers
    on ie.subject_id = oe.subject_id and ie.hadm_id = oe.hadm_id and ie.icustay_id = oe.icustay_id
    -- and ensure the data occurs during the first day
    and oe.charttime between ie.intime and tt.endtime
    where itemid in
    (
    -- these are the most frequently occurring urine output observations in CareVue
    40055, -- "Urine Out Foley"
    43175, -- "Urine ."
    40069, -- "Urine Out Void"
    40094, -- "Urine Out Condom Cath"
    40715, -- "Urine Out Suprapubic"
    40473, -- "Urine Out IleoConduit"
    40085, -- "Urine Out Incontinent"
    40057, -- "Urine Out Rt Nephrostomy"
    40056, -- "Urine Out Lt Nephrostomy"
    40405, -- "Urine Out Other"
    40428, -- "Urine Out Straight Cath"
    40086,--    Urine Out Incontinent
    40096, -- "Urine Out Ureteral Stent #1"
    40651, -- "Urine Out Ureteral Stent #2"

    -- these are the most frequently occurring urine output observations in CareVue
    226559, -- "Foley"
    226560, -- "Void"
    227510, -- "TF Residual"
    226561, -- "Condom Cath"
    226584, -- "Ileoconduit"
    226563, -- "Suprapubic"
    226564, -- "R Nephrostomy"
    226565, -- "L Nephrostomy"
    226567, --    Straight Cath
    226557, -- "R Ureteral Stent"
    226558  -- "L Ureteral Stent"
    )
    group by ie.subject_id, ie.hadm_id, ie.icustay_id
    order by ie.subject_id, ie.hadm_id, ie.icustay_id
    )
    """

    query_qsofa = """
    qsofa_scorecomp as
    (
        select ie.icustay_id
          , v.SysBP_Min
          , v.RespRate_max
          , gcs.MinGCS
        from icustays ie
        left join vitals v
          on ie.icustay_id = v.icustay_id
        left join gcs gcs
          on ie.icustay_id = gcs.icustay_id
    )
    , qsofa_scorecalc as
    (
      -- Calculate the final score
      -- note that if the underlying data is missing, the component is null
      -- eventually these are treated as 0 (normal), but knowing when data is missing is useful for debugging
      select icustay_id
      , case
          when SysBP_Min is null then null
          when SysBP_Min   < 100 then 1
          else 0 end
        as SysBP_score
      , case
          when MinGCS is null then null
          when MinGCS   < 15 then 1
          else 0 end
        as GCS_score
      , case
          when RespRate_max is null then null
          when RespRate_max   >= 22 then 1
          else 0 end
        as RespRate_score
      from qsofa_scorecomp
    )
    , qsofa as
    (
        select ie.subject_id, ie.hadm_id, ie.icustay_id
        , coalesce(SysBP_score,0)
         + coalesce(GCS_score,0)
         + coalesce(RespRate_score,0)
         as qSOFA
        , SysBP_score
        , GCS_score
        , RespRate_score
        from icustays ie
        left join qsofa_scorecalc s
          on ie.icustay_id = s.icustay_id
    )
    """

    # the below query defines the time interval for data extraction
    query_tt = """
    times as
    (
    select
        icustay_id
        , ie.intime as starttime
        , ie.intime + interval '3' hour as endtime
    from icustays ie
    )
    """

    query = 'SET search_path to ' + schema_name + ';' + '\n' \
    + 'with ' + query_tt \
    + ', ' + query_uo \
    + ', ' + query_vent \
    + ', ' + query_vitals \
    + ', ' + query_gcs \
    + ', ' + query_labs \
    + ', ' + query_bgart \
    + ', ' + query_vd \
    + ', ' + query_qsofa \
    + """
    select ie.icustay_id
    , tt.starttime, tt.endtime
    , qsofa.qsofa
    from icustays ie
    left join times tt
        on ie.icustay_id = tt.icustay_id
    left join qsofa
        on ie.icustay_id = qsofa.icustay_id
    order by icustay_id
    """

    #qsofa = pd.read_sql_query(query,con)
    return query
