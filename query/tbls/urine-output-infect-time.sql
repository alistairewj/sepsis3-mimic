drop MATERIALIZED VIEW IF EXISTS uo_si CASCADE;
create MATERIALIZED VIEW uo_si as
select
  -- patient identifiers
  ie.icustay_id

  -- volumes associated with urine output ITEMIDs
  , case
      when max(charttime) = min(charttime)
        then null
      when max(charttime) is not null
        then sum(VALUE)
          / (extract(EPOCH from (max(charttime) - min(charttime)))/60.0/60.0/24.0)
    else null end
    as UrineOutput -- daily urine output
from suspinfect_poe ie
-- Join to the outputevents table to get urine output
left join outputevents oe
-- join on all patient identifiers
on ie.icustay_id = oe.icustay_id
-- and ensure the data occurs during the ICU stay
and oe.charttime
  between ie.si_starttime
      and ie.si_endtime
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
40086,--	Urine Out Incontinent
40096, -- "Urine Out Ureteral Stent #1"
40651, -- "Urine Out Ureteral Stent #2"

-- these are the most frequently occurring urine output observations in Metavision
226559, -- "Foley"
226560, -- "Void"
227510, -- "TF Residual"
226561, -- "Condom Cath"
226584, -- "Ileoconduit"
226563, -- "Suprapubic"
226564, -- "R Nephrostomy"
226565, -- "L Nephrostomy"
226567, --	Straight Cath
226557, -- "R Ureteral Stent"
226558  -- "L Ureteral Stent"
)
group by ie.icustay_id
order by ie.icustay_id;
