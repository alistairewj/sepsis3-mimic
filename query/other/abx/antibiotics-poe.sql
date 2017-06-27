DROP TABLE antibiotics_poe;
CREATE TABLE antibiotics_poe AS
with p as
(
  select prescriptions.*
  , case
    when lower(drug_name_generic) like '%' || lower('adoxa') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('ala-tet') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('alodox') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('amikacin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('amikin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('amoxicillin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('amoxicillin%clavulanate') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('clavulanate') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('ampicillin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('augmentin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('avelox') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('avidoxy') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('azactam') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('azithromycin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('aztreonam') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('axetil') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('bactocill') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('bactrim') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('bethkis') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('biaxin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('bicillin l-a') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cayston') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefazolin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cedax') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefoxitin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('ceftazidime') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefaclor') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefadroxil') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefdinir') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefditoren') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefepime') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefotetan') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefotaxime') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefpodoxime') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefprozil') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('ceftibuten') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('ceftin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefuroxime ') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cefuroxime') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cephalexin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('chloramphenicol') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cipro') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('ciprofloxacin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('claforan') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('clarithromycin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cleocin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('clindamycin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('cubicin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('dicloxacillin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('doryx') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('doxycycline') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('duricef') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('dynacin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('ery-tab') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('eryped') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('eryc') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('erythrocin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('erythromycin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('factive') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('flagyl') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('fortaz') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('furadantin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('garamycin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('gentamicin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('kanamycin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('keflex') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('ketek') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('levaquin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('levofloxacin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('lincocin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('macrobid') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('macrodantin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('maxipime') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('mefoxin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('metronidazole') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('minocin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('minocycline') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('monodox') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('monurol') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('morgidox') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('moxatag') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('moxifloxacin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('myrac') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('nafcillin sodium') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('nicazel doxy 30') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('nitrofurantoin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('noroxin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('ocudox') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('ofloxacin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('omnicef') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('oracea') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('oraxyl') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('oxacillin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('pc pen vk') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('pce dispertab') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('panixine') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('pediazole') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('penicillin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('periostat') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('pfizerpen') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('piperacillin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('tazobactam') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('primsol') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('proquin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('raniclor') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('rifadin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('rifampin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('rocephin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('smz-tmp') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('septra') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('septra ds') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('septra') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('solodyn') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('spectracef') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('streptomycin sulfate') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('sulfadiazine') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('sulfamethoxazole') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('trimethoprim') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('sulfatrim') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('sulfisoxazole') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('suprax') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('synercid') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('tazicef') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('tetracycline') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('timentin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('tobi') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('tobramycin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('trimethoprim') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('unasyn') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('vancocin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('vancomycin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('vantin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('vibativ') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('vibra-tabs') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('vibramycin') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('zinacef') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('zithromax') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('zmax') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('zosyn') || '%' then 1
    when lower(drug_name_generic) like '%' || lower('zyvox') || '%' then 1
  else 0
  end as antibiotic
from prescriptions
)
select
  p.subject_id, p.hadm_id, p.icustay_id
  , p.startdate, p.enddate
  , p.drug_type
  , p.drug
  , p.drug_name_generic

  , p.prod_strength, p.dose_val_rx, p.dose_unit_rx
  , p.route
from p
where p.antibiotic = 1;
