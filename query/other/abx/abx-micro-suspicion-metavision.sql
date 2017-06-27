-- only works for metavision as carevue does not accurately document antibiotics
DROP MATERIALIZED VIEW IF EXISTS SUSPINFECT_MV CASCADE;
CREATE MATERIALIZED VIEW SUSPINFECT_MV as
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
  where linksto = 'inputevents_mv'
)
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
  where statusdescription != 'Rewritten'
)
, ab_tbl as
(
  select
      ie.subject_id, ie.hadm_id, ie.icustay_id, ie.intime, ie.outtime
      , mv.first_antibiotic_name as first_antibiotic_name
      , mv.first_antibiotic_time as first_antibiotic_time
  from icustays ie
  left join mv
      on ie.icustay_id = mv.icustay_id
      and mv.first_antibiotic_time between ie.intime and ie.outtime
      and mv.rn = 1
  where ie.dbsource = 'metavision'
)
, me as
(
  select hadm_id
    , chartdate, charttime
    , spec_type_desc
    , max(case when org_name is not null and org_name != '' then 1 else 0 end) as PositiveCulture
  from microbiologyevents
  group by hadm_id, chartdate, charttime, spec_type_desc
)
, ab_fnl as
(
  select
    ab_tbl.icustay_id, ab_tbl.intime, ab_tbl.outtime
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

    , ROW_NUMBER() over (partition by ab_tbl.icustay_id
      order by coalesce(me72.charttime, me24.charttime, me72.chartdate))
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
, ab_laststg as
(
select
  icustay_id
  -- time of suspected infection: either the culture time (if before antibiotic), or the antibiotic time
  , case
      when first_antibiotic_time > intime + interval '48' hour then null
      when last72_charttime is not null
        then last72_charttime
      when next24_charttime is not null or last72_chartdate is not null
        then first_antibiotic_time
    else null
  end as suspected_infection_time
  -- the specimen that was cultured
  , case
      when first_antibiotic_time > intime + interval '48' hour then null
      when last72_charttime is not null or last72_chartdate is not null
        then last72_specimen
      when next24_charttime is not null
        then next24_specimen
    else null
  end as specimen
  -- whether the cultured specimen ended up being positive or not
  , case
      when first_antibiotic_time > intime + interval '48' hour then null
      when last72_charttime is not null or last72_chartdate is not null
        then last72_positiveculture
      when next24_charttime is not null
        then next24_positiveculture
    else null
  end as positiveculture
from ab_fnl
where rn = 1
)
select
  icustay_id, suspected_infection_time, specimen, positiveculture
  -- the below two fields are used to extract data - modifying them facilitates sensitivity analyses
  , suspected_infection_time - interval '48' hour as si_starttime
  , suspected_infection_time + interval '24' hour as si_endtime
from ab_laststg
order by icustay_id;
