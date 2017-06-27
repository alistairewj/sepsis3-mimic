
--5  CMS Severe Sepsis and Septic Shock: Management Bundle measure (NQF #0500) criteria
-- Adapted by Seymour et al.
-- These criteria require:
-- i) denominator population derived from discharge diagnoses
-- ii) the presence of >=2 SIRS criteria
-- iii) the presence of organ dysfunction using criteria present by international guidelines

-- tables required:
--  sirs
--  vitalsfirstday
--  labsfirstday

-- three steps:
-- 1) identify patients by ICD-9 codes
-- 2) require >= 2 SIRS criteria
-- 3) require organ dysfunction

-- last two steps are required within 24 hours of ICU admission
DROP TABLE IF EXISTS sepsis_nqf_0500 cascade;
CREATE TABLE sepsis_nqf_0500 as
-- denominator population
with dx as
(
  select distinct hadm_id
  from diagnoses_icd
  where icd9_code in
  (
    '0031' -- SALMONELLA SEPTICEMIA
  , '0362' -- MENINGOCOCCEMIA
  , '0380' -- STREPTOCOCCAL SEPTICEMIA
  , '03810' --  STAPH SEPTICEMIA NOS
  , '03811' --  MSSA SEPTICEMIA
  , '03812' --  MRSA SEPTICEMIA
  , '03819' --  STAPH SEPTICEMIA NEC
  , '0382' -- PNEUMOCOCCAL SEPTICEMIA
  , '0383' -- ANAEROBIC SEPTICEMIA
  , '03840' --  GRAM-NEG SEPTICEMIA NOS
  , '03841' --  H. INFLUENZAE SEPTICEMIA
  , '03842' --  E. COLI SEPTICEMIA
  , '03843' --  PSEUDOMONAS SEPTICEMIA
  , '03844' --  SERRATIA SEPTICEMIA
  , '03849' --  GRAM-NEG SEPTICEMIA NEC
  , '0388' -- SEPTICEMIA NEC
  , '0389' -- SEPTICEMIA NOS
  , '78552' --  SEPTIC SHOCK
  , '99591' --  SEPSIS
  , '99592' --  SEVERE SEPSIS
  )
)
-- sirs
, sirs as
(
  select icustay_id, sirs
  , case when sirs >= 2 then 1 else 0 end as sirs_positive
  from sirs
)
-- organ failure
, vitals as
(
  select icustay_id
    , sysbp_min
    , case when sysbp_min < 90 then 1 else 0 end as cardiovascular
  from vitalsfirstday
)
, labs as
(
  select icustay_id
  , creatinine_max
  , bilirubin_max
  , platelet_min
  , inr_max
  , lactate_max
  , case when creatinine_max > 2.0 then 1 else 0 end as renal
  , case when bilirubin_max > 2.0 then 1 else 0 end as hepatic
  , case when platelet_min < 100 then 1 else 0 end as hematologic
  , case when inr_max > 1.5 then 1 else 0 end as coagulation
  , case when lactate_max > 2.0 then 1 else 0 end as metabolism
  from labsfirstday
)
select
  ie.icustay_id
  -- final rule
  , case
      when dx.hadm_id is not null
       and sirs.sirs_positive = 1
       and
       (
        vitals.cardiovascular = 1
        OR labs.renal = 1
        OR labs.hepatic = 1
        OR labs.hematologic = 1
        OR labs.coagulation = 1
        OR labs.metabolism = 1
       )
      then 1
    else 0 end as sepsis
  -- individual components
  , case when dx.hadm_id is not null then 1 else 0 end as sepsis_dx
  , sirs.sirs_positive
  , case when vitals.cardiovascular = 1 then 1
         when labs.renal = 1 then 1
         when labs.hepatic = 1 then 1
         when labs.hematologic = 1 then 1
         when labs.coagulation = 1 then 1
         when labs.metabolism = 1 then 1
      else 0 end as organ_failure
  -- data driving the components
  , sirs.sirs
  , vitals.cardiovascular
  , labs.renal
  , labs.hepatic
  , labs.hematologic
  , labs.coagulation
  , labs.metabolism
from icustays ie
left join dx
  on ie.hadm_id = dx.hadm_id
left join sirs
  on ie.icustay_id = sirs.icustay_id
left join vitals
  on ie.icustay_id = vitals.icustay_id
left join labs
  on ie.icustay_id = labs.icustay_id;
