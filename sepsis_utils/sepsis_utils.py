from __future__ import print_function

import sys
import os
import psycopg2
import pandas as pd
import numpy as np

import roc_utils as ru

from statsmodels.formula.api import logit

import sklearn
from sklearn import cross_validation
from sklearn.grid_search import GridSearchCV
from sklearn import metrics
from sklearn.metrics import auc, roc_curve

# create a database connection

# below config used on pc70
sqluser = 'alistairewj'
dbname = 'mimic'
schema_name = 'mimiciii'

# qSOFA
def get_qsofa(con):
    query = 'SET search_path to ' + schema_name + ';' + \
    """
    select icustay_id
    , qsofa
    , sysbp_score as sysbp_score_qsofa
    , resprate_score as resprate_score_qsofa
    , gcs_score as gcs_score_qsofa
    from qsofa
    order by icustay_id
    """

    qsofa = pd.read_sql_query(query,con)
    return qsofa

# LODS
def get_lods(con):
    query = 'SET search_path to ' + schema_name + ';' + \
    """
    select icustay_id
    , LODS
    , neurologic as neurologic_lods
    , cardiovascular as cardiovascular_lods
    , renal as renal_lods
    , pulmonary as pulmonary_lods
    , hematologic as hematologic_lods
    , hepatic as hepatic_lods
    from lods
    order by icustay_id
    """

    lods = pd.read_sql_query(query,con)
    return lods

# SOFA
def get_sofa(con):
    query = 'SET search_path to ' + schema_name + ';' + \
    """
    select s.*
    from sofa s
    order by s.icustay_id
    """

    sofa = pd.read_sql_query(query,con)
    return sofa

# OASIS
def get_oasis(con):
    query = 'SET search_path to ' + schema_name + ';' + \
    """
    select o.icustay_id, oasis
    from oasis o
    order by o.icustay_id
    """

    oasis = pd.read_sql_query(query,con)
    return oasis


# SIRS
def get_sirs(con):
    query = 'SET search_path to ' + schema_name + ';' + \
    """
    select icustay_id
    , sirs
    , temp_score as temp_score_sirs
    , heartrate_score as heartrate_score_sirs
    , resp_score as resp_score_sirs
    , wbc_score as wbc_score_sirs
    from sirs
    order by icustay_id
    """

    sirs = pd.read_sql_query(query,con)
    return sirs

# angus
def get_angus(con):
    fp = open(os.path.dirname(os.path.realpath(__file__)) + '/../mimic-code/sepsis/angus.sql', 'r')
    query = 'SET search_path to ' + schema_name + ';' + fp.read()
    fp.close()

    cur = con.cursor()
    cur.execute(query)
    cur.close()
    angus = pd.read_sql_query("""select * from angus_sepsis""",con)
    return angus

def get_suspected_infection_time(con):
    # define antibiotics query in a new string
    # this allows us to reuse it later
    query_ab = 'SET search_path to ' + schema_name + ';' + \
    """
    with ab as
    (
    select
      di.*, linksto
      , case
        when lower(label) like '%' || lower('adoxa') || '%' then 1
        when lower(label) like '%' || lower('ala-tet') || '%' then 1
        when lower(label) like '%' || lower('alodox') || '%' then 1
        when lower(label) like '%' || lower('amikacin') || '%' then 1
        when lower(label) like '%' || lower('amikin') || '%' then 1
        when lower(label) like '%' || lower('amoxicillin') || '%' then 1
        when lower(label) like '%' || lower('amoxicillin%clavulanate') || '%' then 1
        when lower(label) like '%' || lower('clavulanate') || '%' then 1
        when lower(label) like '%' || lower('ampicillin') || '%' then 1
        when lower(label) like '%' || lower('augmentin') || '%' then 1
        when lower(label) like '%' || lower('avelox') || '%' then 1
        when lower(label) like '%' || lower('avidoxy') || '%' then 1
        when lower(label) like '%' || lower('azactam') || '%' then 1
        when lower(label) like '%' || lower('azithromycin') || '%' then 1
        when lower(label) like '%' || lower('aztreonam') || '%' then 1
        when lower(label) like '%' || lower('axetil') || '%' then 1
        when lower(label) like '%' || lower('bactocill') || '%' then 1
        when lower(label) like '%' || lower('bactrim') || '%' then 1
        when lower(label) like '%' || lower('bethkis') || '%' then 1
        when lower(label) like '%' || lower('biaxin') || '%' then 1
        when lower(label) like '%' || lower('bicillin l-a') || '%' then 1
        when lower(label) like '%' || lower('cayston') || '%' then 1
        when lower(label) like '%' || lower('cefazolin') || '%' then 1
        when lower(label) like '%' || lower('cedax') || '%' then 1
        when lower(label) like '%' || lower('cefoxitin') || '%' then 1
        when lower(label) like '%' || lower('ceftazidime') || '%' then 1
        when lower(label) like '%' || lower('cefaclor') || '%' then 1
        when lower(label) like '%' || lower('cefadroxil') || '%' then 1
        when lower(label) like '%' || lower('cefdinir') || '%' then 1
        when lower(label) like '%' || lower('cefditoren') || '%' then 1
        when lower(label) like '%' || lower('cefepime') || '%' then 1
        when lower(label) like '%' || lower('cefotetan') || '%' then 1
        when lower(label) like '%' || lower('cefotaxime') || '%' then 1
        when lower(label) like '%' || lower('cefpodoxime') || '%' then 1
        when lower(label) like '%' || lower('cefprozil') || '%' then 1
        when lower(label) like '%' || lower('ceftibuten') || '%' then 1
        when lower(label) like '%' || lower('ceftin') || '%' then 1
        when lower(label) like '%' || lower('cefuroxime ') || '%' then 1
        when lower(label) like '%' || lower('cefuroxime') || '%' then 1
        when lower(label) like '%' || lower('cephalexin') || '%' then 1
        when lower(label) like '%' || lower('chloramphenicol') || '%' then 1
        when lower(label) like '%' || lower('cipro') || '%' then 1
        when lower(label) like '%' || lower('ciprofloxacin') || '%' then 1
        when lower(label) like '%' || lower('claforan') || '%' then 1
        when lower(label) like '%' || lower('clarithromycin') || '%' then 1
        when lower(label) like '%' || lower('cleocin') || '%' then 1
        when lower(label) like '%' || lower('clindamycin') || '%' then 1
        when lower(label) like '%' || lower('cubicin') || '%' then 1
        when lower(label) like '%' || lower('dicloxacillin') || '%' then 1
        when lower(label) like '%' || lower('doryx') || '%' then 1
        when lower(label) like '%' || lower('doxycycline') || '%' then 1
        when lower(label) like '%' || lower('duricef') || '%' then 1
        when lower(label) like '%' || lower('dynacin') || '%' then 1
        when lower(label) like '%' || lower('ery-tab') || '%' then 1
        when lower(label) like '%' || lower('eryped') || '%' then 1
        when lower(label) like '%' || lower('eryc') || '%' then 1
        when lower(label) like '%' || lower('erythrocin') || '%' then 1
        when lower(label) like '%' || lower('erythromycin') || '%' then 1
        when lower(label) like '%' || lower('factive') || '%' then 1
        when lower(label) like '%' || lower('flagyl') || '%' then 1
        when lower(label) like '%' || lower('fortaz') || '%' then 1
        when lower(label) like '%' || lower('furadantin') || '%' then 1
        when lower(label) like '%' || lower('garamycin') || '%' then 1
        when lower(label) like '%' || lower('gentamicin') || '%' then 1
        when lower(label) like '%' || lower('kanamycin') || '%' then 1
        when lower(label) like '%' || lower('keflex') || '%' then 1
        when lower(label) like '%' || lower('ketek') || '%' then 1
        when lower(label) like '%' || lower('levaquin') || '%' then 1
        when lower(label) like '%' || lower('levofloxacin') || '%' then 1
        when lower(label) like '%' || lower('lincocin') || '%' then 1
        when lower(label) like '%' || lower('macrobid') || '%' then 1
        when lower(label) like '%' || lower('macrodantin') || '%' then 1
        when lower(label) like '%' || lower('maxipime') || '%' then 1
        when lower(label) like '%' || lower('mefoxin') || '%' then 1
        when lower(label) like '%' || lower('metronidazole') || '%' then 1
        when lower(label) like '%' || lower('minocin') || '%' then 1
        when lower(label) like '%' || lower('minocycline') || '%' then 1
        when lower(label) like '%' || lower('monodox') || '%' then 1
        when lower(label) like '%' || lower('monurol') || '%' then 1
        when lower(label) like '%' || lower('morgidox') || '%' then 1
        when lower(label) like '%' || lower('moxatag') || '%' then 1
        when lower(label) like '%' || lower('moxifloxacin') || '%' then 1
        when lower(label) like '%' || lower('myrac') || '%' then 1
        when lower(label) like '%' || lower('nafcillin sodium') || '%' then 1
        when lower(label) like '%' || lower('nicazel doxy 30') || '%' then 1
        when lower(label) like '%' || lower('nitrofurantoin') || '%' then 1
        when lower(label) like '%' || lower('noroxin') || '%' then 1
        when lower(label) like '%' || lower('ocudox') || '%' then 1
        when lower(label) like '%' || lower('ofloxacin') || '%' then 1
        when lower(label) like '%' || lower('omnicef') || '%' then 1
        when lower(label) like '%' || lower('oracea') || '%' then 1
        when lower(label) like '%' || lower('oraxyl') || '%' then 1
        when lower(label) like '%' || lower('oxacillin') || '%' then 1
        when lower(label) like '%' || lower('pc pen vk') || '%' then 1
        when lower(label) like '%' || lower('pce dispertab') || '%' then 1
        when lower(label) like '%' || lower('panixine') || '%' then 1
        when lower(label) like '%' || lower('pediazole') || '%' then 1
        when lower(label) like '%' || lower('penicillin') || '%' then 1
        when lower(label) like '%' || lower('periostat') || '%' then 1
        when lower(label) like '%' || lower('pfizerpen') || '%' then 1
        when lower(label) like '%' || lower('piperacillin') || '%' then 1
        when lower(label) like '%' || lower('tazobactam') || '%' then 1
        when lower(label) like '%' || lower('primsol') || '%' then 1
        when lower(label) like '%' || lower('proquin') || '%' then 1
        when lower(label) like '%' || lower('raniclor') || '%' then 1
        when lower(label) like '%' || lower('rifadin') || '%' then 1
        when lower(label) like '%' || lower('rifampin') || '%' then 1
        when lower(label) like '%' || lower('rocephin') || '%' then 1
        when lower(label) like '%' || lower('smz-tmp') || '%' then 1
        when lower(label) like '%' || lower('septra') || '%' then 1
        when lower(label) like '%' || lower('septra ds') || '%' then 1
        when lower(label) like '%' || lower('septra') || '%' then 1
        when lower(label) like '%' || lower('solodyn') || '%' then 1
        when lower(label) like '%' || lower('spectracef') || '%' then 1
        when lower(label) like '%' || lower('streptomycin sulfate') || '%' then 1
        when lower(label) like '%' || lower('sulfadiazine') || '%' then 1
        when lower(label) like '%' || lower('sulfamethoxazole') || '%' then 1
        when lower(label) like '%' || lower('trimethoprim') || '%' then 1
        when lower(label) like '%' || lower('sulfatrim') || '%' then 1
        when lower(label) like '%' || lower('sulfisoxazole') || '%' then 1
        when lower(label) like '%' || lower('suprax') || '%' then 1
        when lower(label) like '%' || lower('synercid') || '%' then 1
        when lower(label) like '%' || lower('tazicef') || '%' then 1
        when lower(label) like '%' || lower('tetracycline') || '%' then 1
        when lower(label) like '%' || lower('timentin') || '%' then 1
        when lower(label) like '%' || lower('tobi') || '%' then 1
        when lower(label) like '%' || lower('tobramycin') || '%' then 1
        when lower(label) like '%' || lower('trimethoprim') || '%' then 1
        when lower(label) like '%' || lower('unasyn') || '%' then 1
        when lower(label) like '%' || lower('vancocin') || '%' then 1
        when lower(label) like '%' || lower('vancomycin') || '%' then 1
        when lower(label) like '%' || lower('vantin') || '%' then 1
        when lower(label) like '%' || lower('vibativ') || '%' then 1
        when lower(label) like '%' || lower('vibra-tabs') || '%' then 1
        when lower(label) like '%' || lower('vibramycin') || '%' then 1
        when lower(label) like '%' || lower('zinacef') || '%' then 1
        when lower(label) like '%' || lower('zithromax') || '%' then 1
        when lower(label) like '%' || lower('zmax') || '%' then 1
        when lower(label) like '%' || lower('zosyn') || '%' then 1
        when lower(label) like '%' || lower('zyvox') || '%' then 1
      else 0
      end as antibiotic
    from mimiciii.d_items di
    where linksto = 'inputevents_cv'
    or linksto = 'inputevents_mv'
    )
    """

    query_abtbl = \
    """
    , mv as
    (
    select icustay_id
    , label as first_antibiotic_name
    , starttime as first_antibiotic_time
    , ROW_NUMBER() over (partition by icustay_id order by starttime, endtime) as rn
    from inputevents_mv mv
    inner join ab
        on mv.itemid = ab.itemid
        and ab.antibiotic = 1
    )
    , cv as
    (
    select icustay_id
    , label as first_antibiotic_name
    , charttime as first_antibiotic_time
    , ROW_NUMBER() over (partition by icustay_id order by charttime) as rn
    from inputevents_cv cv
    inner join ab
        on cv.itemid = ab.itemid
        and ab.antibiotic = 1
    )
    , ab_tbl as
    (
    select
        ie.subject_id, ie.hadm_id, ie.icustay_id
        , coalesce(cv.first_antibiotic_name, mv.first_antibiotic_name) as first_antibiotic_name
        , coalesce(cv.first_antibiotic_time, mv.first_antibiotic_time) as first_antibiotic_time
    from icustays ie
    left join mv
        on ie.icustay_id = mv.icustay_id
        and mv.first_antibiotic_time between ie.intime and ie.intime + interval '24' hour
        and mv.rn = 1
    left join cv
        on ie.icustay_id = cv.icustay_id
        and cv.first_antibiotic_time between ie.intime and ie.intime + interval '24' hour
        and cv.rn = 1
    )
    """

    # the above defines antibiotics given IV
    # the next block adds in blood cultures
    # it also adds in the logic to define the time of suspected infection

    query = query_ab + query_abtbl + \
    """
    , me as
    (
    select hadm_id
      , chartdate, charttime
      , spec_type_desc
      , max(case when org_name is not null and org_name != '' then 1 else 0 end) as PositiveCulture
    from mimiciii.microbiologyevents
    group by hadm_id, chartdate, charttime, spec_type_desc
    )
    , ab_fnl as
    (
    select
      ab_tbl.icustay_id
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

      , ROW_NUMBER() over (partition by ab_tbl.icustay_id order by coalesce(me72.charttime, me24.charttime, me72.chartdate))
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
    select
      ab_fnl.icustay_id
      -- time of suspected infection: either the culture time (if before antibiotic), or the antibiotic time
      , case
          when last72_charttime is not null
            then last72_charttime
          when next24_charttime is not null or last72_chartdate is not null
            then first_antibiotic_time
        else null
      end as suspected_infection_time
      -- the specimen that was cultured
      , case
          when last72_charttime is not null or last72_chartdate is not null
            then last72_specimen
          when next24_charttime is not null
            then next24_specimen
        else null
      end as specimen
      -- whether the cultured specimen ended up being positive or not
      , case
          when last72_charttime is not null or last72_chartdate is not null
            then last72_positiveculture
          when next24_charttime is not null
            then next24_positiveculture
        else null
      end as positiveculture
    from ab_fnl
    where rn = 1
    order by icustay_id;
    """

    ab = pd.read_sql_query(query,con)
    return ab

def get_other_data(con):
    query = 'SET search_path to ' + schema_name + ';' + \
    """
    with t1 as
    (
    select ie.icustay_id, ie.hadm_id
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
    )
    select
        icustay_id
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
        , icu_los
    from t1;
    """

    misc = pd.read_sql_query(query,con)
    return misc


def get_physiologic_data(con):
    query = 'SET search_path to ' + schema_name + ';' + \
    """
    with bg as
    (
    select
        icustay_id
        , min(PH) as ArterialPH_Min
        , max(PH) as ArterialPH_Max
        , min(PCO2) as PaCO2_Min
        , max(PCO2) as PaCO2_Max
        , min(PaO2FiO2) as PaO2FiO2_Min
        , min(AaDO2) as AaDO2_Min
    from bloodgasfirstdayarterial
    where SPECIMEN_PRED = 'ART'
    group by icustay_id
    )
    , vent as
    (
    select
        ie.icustay_id
        , max(case when vd.icustay_id is not null then 1 else 0 end)
            as MechVent
    from icustays ie
    left join ventdurations vd
        on ie.icustay_id = vd.icustay_id
        and vd.starttime <= ie.intime + interval '1' day
    group by ie.icustay_id
    )
    , vaso as
    (
    select
        ie.icustay_id
        , max(case when vd.icustay_id is not null then 1 else 0 end)
            as Vasopressor
    from icustays ie
    left join vasopressordurations vd
        on ie.icustay_id = vd.icustay_id
        and vd.starttime <= ie.intime + interval '1' day
    group by ie.icustay_id

    )
    select
        ie.icustay_id
        , vit.HeartRate_Min
        , vit.HeartRate_Max
        , vit.SysBP_Min
        , vit.SysBP_Max
        , vit.DiasBP_Min
        , vit.DiasBP_Max
        , vit.MeanBP_Min
        , vit.MeanBP_Max
        , vit.RespRate_Min
        , vit.RespRate_Max
        , vit.TempC_Min
        , vit.TempC_Max
        , vit.SpO2_Min
        , vit.SpO2_Max


        -- coalesce lab/vital sign glucose
        , case
            when vit.Glucose_min < lab.Glucose_Min
                then vit.Glucose_Min
            when lab.Glucose_Min < vit.Glucose_Min
                then lab.Glucose_Min
            else coalesce(vit.Glucose_Min, lab.Glucose_Min)
        end as Glucose_Min

        , case
            when vit.Glucose_Max > 2000 and lab.Glucose_Max > 2000
                then null
            when vit.Glucose_Max > 2000
                then lab.Glucose_Max
            when lab.Glucose_Max > 2000
                then vit.Glucose_Max
            when vit.Glucose_Max > lab.Glucose_Max
                then vit.Glucose_Max
            when lab.Glucose_Max > vit.Glucose_Max
                then lab.Glucose_Max
            else null
        end as Glucose_Max

        , gcs.MinGCS as GCS_Min

        -- height in centimetres
        , case
            when ht.Height > 100
             and ht.Height < 250
                 then ht.Height
            else null
        end as Height

        -- weight in kgs
        , case
            when wt.Weight > 30
             and wt.Weight < 300
                 then wt.Weight
            else null
        end as Height


        , lab.ANIONGAP_min
        , lab.ANIONGAP_max
        , lab.ALBUMIN_min
        , lab.ALBUMIN_max
        , lab.BANDS_min
        , lab.BANDS_max
        , lab.BICARBONATE_min
        , lab.BICARBONATE_max
        , lab.BILIRUBIN_min
        , lab.BILIRUBIN_max
        , lab.CREATININE_min
        , lab.CREATININE_max
        , lab.CHLORIDE_min
        , lab.CHLORIDE_max

        , lab.HEMATOCRIT_min
        , lab.HEMATOCRIT_max
        , lab.HEMOGLOBIN_min
        , lab.HEMOGLOBIN_max
        , lab.LACTATE_min
        , lab.LACTATE_max
        , lab.PLATELET_min
        , lab.PLATELET_max
        , lab.POTASSIUM_min
        , lab.POTASSIUM_max
        , lab.INR_min
        , lab.INR_max

        --, lab.PTT_min
        --, lab.PTT_max
        --, lab.PT_min
        --, lab.PT_max

        , lab.SODIUM_min
        , lab.SODIUM_max
        , lab.BUN_min
        , lab.BUN_max
        , lab.WBC_min
        , lab.WBC_max

        , rrt.RRT

        , case
            when uo.UrineOutput > 20000
                then null
            else uo.UrineOutput
        end as UrineOutput

        , vent.MechVent
        , vaso.Vasopressor

        , bg.AADO2_min
        , case
            when bg.PaO2FiO2_min > 1000
                then null
            else bg.PaO2FiO2_min
        end as PaO2FiO2_min
        , bg.ArterialPH_min
        , bg.ArterialPH_max
        , bg.PaCO2_min
        , bg.PaCO2_max

    from icustays ie
    left join vitalsfirstday vit
        on ie.icustay_id = vit.icustay_id
    left join gcsfirstday gcs
        on ie.icustay_id = gcs.icustay_id
    left join heightfirstday ht
        on ie.icustay_id = ht.icustay_id
    left join weightfirstday wt
        on ie.icustay_id = wt.icustay_id
    left join labsfirstday lab
        on ie.icustay_id = lab.icustay_id
    left join rrtfirstday rrt
        on ie.icustay_id = rrt.icustay_id
    left join uofirstday uo
        on ie.icustay_id = uo.icustay_id
    left join vent
        on ie.icustay_id = vent.icustay_id
    left join vaso
        on ie.icustay_id = vaso.icustay_id
    left join bg
        on ie.icustay_id = bg.icustay_id
    """

    dd = pd.read_sql_query(query,con)
    return dd

def get_cohort(con):
    query = 'SET search_path to ' + schema_name + ';' + \
    """
    with t1 as
    (
    select ie.icustay_id, ie.hadm_id, ie.intime, ie.outtime, yr.year
        , ROW_NUMBER() over (partition by ie.subject_id order by intime) as rn
    from icustays ie
    inner join patients pat
        on ie.subject_id = pat.subject_id
        and pat.dob < ie.intime - interval '16' year
    inner join admissionyear yr
        on ie.hadm_id = yr.hadm_id
    )
    select
        icustay_id, hadm_id, intime, outtime, year
    from t1
    where rn = 1
    """

    cohort = pd.read_sql_query(query,con)
    return cohort

def print_cm(y, yhat):
    print('\nConfusion matrix')
    cm = metrics.confusion_matrix(y, yhat)
    TN = cm[0,0]
    FP = cm[0,1]
    FN = cm[1,0]
    TP = cm[1,1]
    N = TN+FP+FN+TP
    print('   \t{:6s}\t{:6s}'.format('yhat=0','yhat=1'))
    print('y=0\t{:6g}\t{:6g}\tNPV={:2.2f}'.format(cm[0,0],cm[0,1], 100.0*TN / (TN+FN))) # NPV
    print('y=1\t{:6g}\t{:6g}\tPPV={:2.2f}'.format(cm[1,0],cm[1,1], 100.0*TP / (TP+FP))) # PPV
    # add sensitivity/specificity as the bottom line
    print('   \t{:2.2f}\t{:2.2f}\tAcc={:2.2f}'.format(100.0*TN/(TN+FP), 100.0*TP/(TP+FN), 100.0*(TP+TN)/N))
    print('   \tSpec\tSens')

def print_op_stats(yhat_all, y_all, yhat_names=None, header=None, idx=None):
    # for a given set of predictions, prints a table of the performances
    # yhat_all should be an 1xM list containing M numpy arrays of length N
    # y_all is either an Nx1 numpy array (if evaluating against the same outcome)
    # ... or it's an 1xM list containing M numpy arrays of length N

    if 'numpy' in str(type(y_all)):
        # targets input as a single array
        # we create a 1xM list the same size as yhat_all
        y_all = [y_all for i in range(len(yhat_all))]

    stats_names = [ 'TN','FP','FN','TP','Sens','Spec','PPV','NPV','F1','DOR']
    stats_all = np.zeros( [len(yhat_all), len(stats_names)])

    TN = np.zeros(len(yhat_all))
    FP = np.zeros(len(yhat_all))
    FN = np.zeros(len(yhat_all))
    TP = np.zeros(len(yhat_all))

    for i, yhat in enumerate(yhat_all):
        if idx is not None:
            cm = metrics.confusion_matrix(y_all[i][idx[i]], yhat[idx[i]])
        else:
            cm = metrics.confusion_matrix(y_all[i], yhat)

        # confusion matrix is output as int64 - we'd like to calculate percentages
        cm = cm.astype(float)

        # to make the code clearer, extract components from confusion matrix
        TN = cm[0,0] # true negatives
        FP = cm[0,1] # false positives
        FN = cm[1,0] # false negatives
        TP = cm[1,1] # true positives
        stats_all[i,4] = 100.0*TP/(TP+FN) # Sensitivity
        stats_all[i,5] = 100.0*TN/(TN+FP) # Specificity
        stats_all[i,6] = 100.0*TP/(TP+FP) # PPV
        stats_all[i,7] = 100.0*TN/(TN+FN) # NPV

        # F1, the harmonic mean of PPV/Sensitivity
        stats_all[i,8] = 2.0*(stats_all[i,6] * stats_all[i,4]) / (stats_all[i,6] + stats_all[i,4])
        stats_all[i,9] = (TP/FP)/(FN/TN) # diagnostic odds ratio

        # now push the stats to the final stats vector
        stats_all[i,0] = TN
        stats_all[i,1] = FP
        stats_all[i,2] = FN
        stats_all[i,3] = TP


    print('Metric')
    if header is not None:
        for i, hdr_name in enumerate(header):
            print('\t{:5s}'.format(hdr_name), end='')
        print('') # newline

    # print the names of the predictions, if they were provided
    print('') # newline
    if yhat_names is not None:
        for i, yhat_name in enumerate(yhat_names):
            print('\t{:5s}'.format(yhat_name), end='')
        print('') # newline

    # print the stats calculated
    for n, stats_name in enumerate(stats_names):
        print('{:5s}'.format(stats_name), end='')
        for i, yhat_name in enumerate(yhat_names):
            if n < 4: # use integer format for the tp/fp
                print('\t{:5.0f}'.format(stats_all[i,n]), end='')
            else: # use decimal format for the sensitivity, specificity, etc
                print('\t{:5.2f}'.format(stats_all[i,n]), end='')

        print('') # newline

    return stats_all

def print_stats_to_file(filename, yhat_names, stats_all):
    # print the table to a file for convenient viewing
    f = open(filename,'w')
    stats_names = [ 'TN','FP','FN','TP','N','Sens','Spec','PPV','NPV','F1','DOR']

    f.write('Subgroup')
    for n, stats_name in enumerate(stats_names):
        f.write('\t%s' % stats_name)

    f.write('\n')

    for i, yhat_name in enumerate(yhat_names):
        f.write('%s' % yhat_name)

        for n, stats_name in enumerate(stats_names):
            if n < 5: # use integer format for the tp/fp
                f.write('\t%10.0f' % stats_all[i,n])
            else: # use decimal format for the sensitivity, specificity, etc
                f.write('\t%10.2f' % stats_all[i,n])

        f.write('\n') # newline

    f.close()

def print_demographics(df):
    all_vars = ['age','gender','bmi','hospital_expire_flag','thirtyday_expire_flag',
      'icu_los','hosp_los','mech_vent'] #

    for i, curr_var in enumerate(all_vars):
        if curr_var in df.columns:
            if curr_var in ['age','bmi','icu_los']: # report mean +- STD
                print('{:20s}\t{:2.2f} +- {:2.2f}'.format(curr_var, df[curr_var].mean(), df[curr_var].std()))
            elif curr_var in ['gender']: # convert from M/F
                print('{:20s}\t{:2.2f}%'.format(curr_var, 100.0*np.sum(df[curr_var].values=='M').astype(float) / df.shape[0]))
            elif curr_var in ['hospital_expire_flag','thirtyday_expire_flag','mech_vent']:
                print('{:20s}\t{:2.2f}%'.format(curr_var, 100.0*(df[curr_var].mean()).astype(float)))
                # binary, report percentage

        else:
            print('{:20s}'.format(curr_var))

def print_auc_table(df, preds_header, target_header):
    # prints a table of AUROCs and p-values like what was presented in the sepsis 3 paper
    preds = [df[x].values for x in preds_header]
    y = df[target_header].values == 1
    P = len(preds)

    print('{:5s}'.format(''),end='\t')

    for p in range(P):
        print('{:20s}'.format(preds_header[p]),end='\t')

    print('')

    for p in range(P):
        print('{:5s}'.format(preds_header[p]),end='\t')
        for q in range(P):
            if p==q:
                auc, ci = ru.bootstrap_auc(preds[p], y, B=100)
                print('{:0.3f} [{:0.3f}, {:0.3f}]'.format(auc, ci[0], ci[1]), end='\t')
            elif q>p:
                #TODO: cronenback alpha
                print('{:20s}'.format(''),end='\t')

            else:
                pval, ci = ru.test_auroc(preds[p], preds[q], y)
                if pval > 0.001:
                    print('{:0.3f}{:15s}'.format(pval, ''), end='\t')
                else:
                    print('< 0.001{:15s}'.format(''),end='\t')


        print('')


def print_auc_table_baseline(df, preds_header, target_header):
    # prints a table of AUROCs and p-values
    # also train the baseline model using df_mdl

    P = len(preds_header)
    y = df[target_header].values == 1

    print('{:5s}'.format(''),end='\t')

    preds = list()
    for p in range(P):
        score_added = preds_header[p]
        print('{:20s}'.format(preds_header[p]),end='\t')

        # build the models and get the predictions
        model = logit(formula=target_header + " ~ age + elixhauser_hospital" +
        " + race_black + race_other + is_male + " + score_added,
        data=df).fit(disp=0)

        # create a list, each element containing the predictions
        # we will update this to be model predictions
        preds.append(model.predict())

    print('')

    for p in range(P):
        print('{:5s}'.format(preds_header[p]),end='\t')

        for q in range(P):
            if p==q:
                auc, ci = ru.bootstrap_auc(preds[p], y, B=100)
                print('{:0.3f} [{:0.3f}, {:0.3f}]'.format(auc, ci[0], ci[1]), end='\t')
            elif q>p:
                #TODO: cronenback alpha
                print('{:20s}'.format(''),end='\t')

            else:
                pval, ci = ru.test_auroc(preds[p], preds[q], y)
                if pval > 0.001:
                    print('{:0.3f}{:15s}'.format(pval, ''), end='\t')
                else:
                    print('< 0.001{:15s}'.format(''),end='\t')


        print('')


def print_auc_table_given_preds(preds, target, preds_header=None):
    # prints a table of AUROCs and p-values
    # also train the baseline model using df_mdl
    # preds is a dictionary of predictions
    
    if preds_header is None:
        preds_header = preds.keys()

    P = len(preds_header)
    y = target == 1

    print('{:5s}'.format(''),end='\t')

    # print header line
    for p in range(P):
        print('{:20s}'.format(preds_header[p]),end='\t')
    print('')

    for p in range(P):
        print('{:5s}'.format(preds_header[p]),end='\t')
        pname = preds_header[p]

        for q in range(P):
            qname = preds_header[q]
            if pname not in preds:
                print('{:20s}'.format(''),end='\t') # skip this as we do not have the prediction
            elif p==q:
                auc, ci = ru.bootstrap_auc(preds[pname], y, B=100)
                print('{:0.3f} [{:0.3f}, {:0.3f}]'.format(auc, ci[0], ci[1]), end='\t')
            elif q>p:
                #TODO: cronenback alpha
                print('{:20s}'.format(''),end='\t')

            else:
                if qname not in preds:
                    print('{:20s}'.format(''),end='\t') # skip this as we do not have the prediction
                else:
                    pval, ci = ru.test_auroc(preds[pname], preds[qname], y)
                    if pval > 0.001:
                        print('{:0.3f}{:15s}'.format(pval, ''), end='\t')
                    else:
                        print('< 0.001{:15s}'.format(''),end='\t')


        print('')
