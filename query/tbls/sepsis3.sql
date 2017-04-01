DROP TABLE IF EXISTS SEPSIS3 CASCADE;
CREATE TABLE SEPSIS3 AS
select co.icustay_id, co.hadm_id
    , co.intime, co.outtime
    , coalesce(co.micro_charttime, co.micro_chartdate) as suspected_infection_time
    , extract(EPOCH from co.intime - coalesce(co.micro_charttime, co.micro_chartdate))
          / 60.0 / 60.0 / 24.0 as suspected_infection_time_days
    , co.positiveculture

    , round((cast(adm.admittime as date) - cast(pat.dob as date)) / 365.242, 4) as age
    , pat.gender
    , adm.ethnicity

    -- ethnicity flags
    , case when adm.ethnicity in
    (
         'WHITE' --  40996
       , 'WHITE - RUSSIAN' --    164
       , 'WHITE - OTHER EUROPEAN' --     81
       , 'WHITE - BRAZILIAN' --     59
       , 'WHITE - EASTERN EUROPEAN' --     25
    ) then 1 else 0 end as race_white
    , case when adm.ethnicity in
    (
          'BLACK/AFRICAN AMERICAN' --   5440
        , 'BLACK/CAPE VERDEAN' --    200
        , 'BLACK/HAITIAN' --    101
        , 'BLACK/AFRICAN' --     44
        , 'CARIBBEAN ISLAND' --      9
    ) then 1 else 0 end as race_black
    , case when adm.ethnicity in
    (
      'HISPANIC OR LATINO' --   1696
    , 'HISPANIC/LATINO - PUERTO RICAN' --    232
    , 'HISPANIC/LATINO - DOMINICAN' --     78
    , 'HISPANIC/LATINO - GUATEMALAN' --     40
    , 'HISPANIC/LATINO - CUBAN' --     24
    , 'HISPANIC/LATINO - SALVADORAN' --     19
    , 'HISPANIC/LATINO - CENTRAL AMERICAN (OTHER)' --     13
    , 'HISPANIC/LATINO - MEXICAN' --     13
    , 'HISPANIC/LATINO - COLOMBIAN' --      9
    , 'HISPANIC/LATINO - HONDURAN' --      4
  ) then 1 else 0 end as race_hispanic

    -- other races
    -- , 'ASIAN' --   1509
    -- , 'ASIAN - CHINESE' --    277
    -- , 'ASIAN - ASIAN INDIAN' --     85
    -- , 'ASIAN - VIETNAMESE' --     53
    -- , 'ASIAN - FILIPINO' --     25
    -- , 'ASIAN - CAMBODIAN' --     17
    -- , 'ASIAN - OTHER' --     17
    -- , 'ASIAN - KOREAN' --     13
    -- , 'ASIAN - JAPANESE' --      7
    -- , 'ASIAN - THAI' --      4
    --
    -- , 'UNKNOWN/NOT SPECIFIED' --   4523
    -- , 'OTHER' --   1512
    -- , 'UNABLE TO OBTAIN' --    814
    -- , 'PATIENT DECLINED TO ANSWER' --    559
    -- , 'MULTI RACE ETHNICITY' --    130
    -- , 'PORTUGUESE' --     61
    -- , 'AMERICAN INDIAN/ALASKA NATIVE' --     51
    -- , 'MIDDLE EASTERN' --     43
    -- , 'NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER' --     18
    -- , 'SOUTH AMERICAN' --      8
    -- , 'AMERICAN INDIAN/ALASKA NATIVE FEDERALLY RECOGNIZED TRIBE' --      3

    , eli.metastatic_cancer
    , case when eli.diabetes_uncomplicated = 1
            or eli.diabetes_complicated = 1
                then 1
        else 0 end as diabetes

    , ht.Height
    , wt.Weight
    , wt.Weight / (ht.Height/100*ht.Height/100) as bmi

    -- service type on hospital admission
    , co.first_service

    , adm.HOSPITAL_EXPIRE_FLAG
    , case when pat.dod <= adm.admittime + interval '30' day then 1 else 0 end
        as THIRTYDAY_EXPIRE_FLAG
    , ie.los as icu_los
    , extract(epoch from (adm.dischtime - adm.admittime))/60.0/60.0/24.0 as hosp_los

    , a.angus
      -- in-hospital mortality score
    ,   CONGESTIVE_HEART_FAILURE    *(4)    + CARDIAC_ARRHYTHMIAS   *(4) +
        VALVULAR_DISEASE            *(-3)   + PULMONARY_CIRCULATION *(0) +
        PERIPHERAL_VASCULAR         *(0)    + HYPERTENSION*(-1) + PARALYSIS*(0) +
        OTHER_NEUROLOGICAL          *(7)    + CHRONIC_PULMONARY*(0) +
        DIABETES_UNCOMPLICATED      *(-1)   + DIABETES_COMPLICATED*(-4) +
        HYPOTHYROIDISM              *(0)    + RENAL_FAILURE*(3) + LIVER_DISEASE*(4) +
        PEPTIC_ULCER                *(-9)   + AIDS*(0) + LYMPHOMA*(7) +
        METASTATIC_CANCER           *(9)    + SOLID_TUMOR*(0) + RHEUMATOID_ARTHRITIS*(0) +
        COAGULOPATHY                *(3)    + OBESITY*(-5) +
        WEIGHT_LOSS                 *(4)    + FLUID_ELECTROLYTE         *(6) +
        BLOOD_LOSS_ANEMIA           *(0)    + DEFICIENCY_ANEMIAS      *(-4) +
        ALCOHOL_ABUSE               *(0)    + DRUG_ABUSE*(-6) +
        PSYCHOSES                   *(-5)   + DEPRESSION*(-8)
    as elixhauser_hospital

    , labs.lactate_max
    , case when vent.starttime is not null then 1 else 0 end as vent

    , so.sofa as sofa
    , lo.lods as lods
    , ml.mlods as mlods

    -- admission SIRS
    , siadm.sirs as sirs
    , si.sirs as sirs_24hours

    -- admission qSOFA
    -- this includes vent/vaso flags
    , qsadm.qsofa as qsofa
    , qsadm.qsofa_no_rx as qsofa_norx
    , qs.qsofa as qsofa_24hours

    -- subcomponents for qSOFA
    , qsadm.SysBP_score as qsofa_sysbp_score
    , qsadm.GCS_score as qsofa_gcs_score
    , qsadm.RespRate_score as qsofa_resprate_score

    -- subcomponents for qSOFA with no treatments
    , qsadm.SysBP_score_norx as qsofa_sysbp_score_norx
    , qsadm.GCS_score_norx as qsofa_gcs_score_norx
    , qsadm.RespRate_score_norx as qsofa_resprate_score_norx

from sepsis3_cohort co
inner join icustays ie
  on co.icustay_id = ie.icustay_id
inner join admissions adm
  on ie.hadm_id = adm.hadm_id
inner join patients pat
  on ie.subject_id = pat.subject_id
left join elixhauser_ahrq eli
  on ie.hadm_id = eli.hadm_id
left join heightfirstday ht
  on ie.icustay_id = ht.icustay_id
left join weightfirstday wt
  on ie.icustay_id = wt.icustay_id
left join ANGUS_SEPSIS a
  on ie.hadm_id = a.hadm_id
left join labsfirstday labs
  on ie.icustay_id = labs.icustay_id
left join
  ( select icustay_id, min(starttime) as starttime
    from ventdurations
    group by icustay_id
  ) vent
  on co.icustay_id = vent.icustay_id
  and vent.starttime >= co.intime - interval '4' hour
  and vent.starttime <= co.intime + interval '1' day
left join SOFA so
  on co.icustay_id = so.icustay_id
left join SIRS si
  on co.icustay_id = si.icustay_id
left join LODS lo
  on co.icustay_id = lo.icustay_id
left join MLODS ml
  on co.icustay_id = ml.icustay_id
left join QSOFA qs
  on co.icustay_id = qs.icustay_id
left join QSOFA_admit qsadm
  on co.icustay_id = qsadm.icustay_id
left join SIRS_admit siadm
  on co.icustay_id = siadm.icustay_id
-- exclusion criteria
where co.excluded = 0
order by co.icustay_id;
