DROP MATERIALIZED VIEW IF EXISTS SEPSIS3 CASCADE;
CREATE MATERIALIZED VIEW SEPSIS3 AS
with t1 as
(
select ie.icustay_id, ie.hadm_id
    , ie.intime, ie.outtime
    , round((cast(adm.admittime as date) - cast(pat.dob as date)) / 365.242, 4) as age
    , pat.gender
    , adm.ethnicity

    , eli.metastatic_cancer
    , case when eli.diabetes_uncomplicated = 1
            or eli.diabetes_complicated = 1
                then 1
        else 0 end as diabetes

    , ht.Height
    , wt.Weight
    , adm.HOSPITAL_EXPIRE_FLAG
    , case when pat.dod <= adm.admittime + interval '30' day then 1 else 0 end
        as THIRTYDAY_EXPIRE_FLAG
    , a.angus
      -- in-hospital mortality score
     ,
    CONGESTIVE_HEART_FAILURE    *(4)    + CARDIAC_ARRHYTHMIAS   *(4) +
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
      AS elixhauser_hospital
    , ie.los as icu_los
from icustays ie
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
left join ANGUS a
    on ie.hadm_id = a.hadm_id
)
, firststay as
(
select ie.icustay_id
    , case
        when pat.dob < ie.intime - interval '16' year
          then 1
      else 0 end as adult
    , ROW_NUMBER() over (partition by ie.subject_id order by intime) as rn
from icustays ie
inner join patients pat
    on ie.subject_id = pat.subject_id
)
select
      t1.icustay_id
    , t1.intime, t1.outtime
    , s.suspected_infection_time
    , s.positiveculture
    , age
    , gender
    , ethnicity
    , metastatic_cancer
    , diabetes
    , elixhauser_hospital
    , height -- in centimetres
    , weight -- in kilograms
    , weight / (height/100*height/100) as bmi
    , HOSPITAL_EXPIRE_FLAG
    , THIRTYDAY_EXPIRE_FLAG
    , angus
    , icu_los

    , sofa.sofa as sofa_si
    , sirs.sirs as sirs_si
    , lods.lods as lods_si
    -- modified lods "did not contain urine output ..., prothrombin, or urea levels"
    , mlods.mlods as mlods_si
    , qsofa.qsofa as qsofa_si
    , case
        when sofa.sofa >= 2 and qsofa.qsofa >= 2 then 1
      else 0 end as sepsis3_si

    , so.sofa as sofa
    , si.sirs as sirs
    , lo.lods as lods
    , qs.qsofa as qsofa
    , case
        when so.sofa >= 2 and qs.qsofa >= 2 then 1
      else 0 end as sepsis3
    , ml.mlods as mlods

    , firststay.rn as icustay_num
    , firststay.adult
from t1
inner join firststay
  on t1.icustay_id = firststay.icustay_id
inner join suspinfect s
  on t1.icustay_id = s.icustay_id
left join SOFA_si sofa
  on t1.icustay_id = sofa.icustay_id
left join SIRS_si sirs
  on t1.icustay_id = sirs.icustay_id
left join LODS_si lods
  on t1.icustay_id = lods.icustay_id
left join MLODS_si mlods
  on t1.icustay_id = mlods.icustay_id
left join QSOFA_si qsofa
  on t1.icustay_id = qsofa.icustay_id
left join SOFA so
  on t1.icustay_id = so.icustay_id
left join SIRS si
  on t1.icustay_id = si.icustay_id
left join LODS lo
  on t1.icustay_id = lo.icustay_id
left join MLODS ml
  on t1.icustay_id = ml.icustay_id
left join QSOFA qs
  on t1.icustay_id = qs.icustay_id

order by t1.icustay_id;
