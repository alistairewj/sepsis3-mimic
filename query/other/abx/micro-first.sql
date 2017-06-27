-- `micro-first.sql`
-- Get time of first microbiology culture

DROP TABLE IF EXISTS micro_first CASCADE;
CREATE TABLE micro_first as
select
  t1.*
from
(
  select me.hadm_id
  , chartdate, charttime
  , spec_type_desc
  , max(case when org_name is not null and org_name != '' then 1 else 0 end) as PositiveCulture
  , sum(case when ab_name is not null and org_name != '' then 1 else 0 end) as NumAbx
  , ROW_NUMBER() over (partition by me.hadm_id order by chartdate, charttime) as rn
  from microbiologyevents me
  where me.spec_itemid in
  (
     -- itemid |                          label                           | numpat | numobs | numabx
     --   -----+----------------------------------------------------------+--------+--------+--------
      70079 -- | URINE                                                    |  24322 | 137558 |  78088
    , 70012 -- | BLOOD CULTURE                                            |  21369 | 179930 |  46168
    , 70091 -- | MRSA SCREEN                                              |  18173 |  32280 |   2395
    , 70062 -- | SPUTUM                                                   |  11154 |  99887 |  70972
    , 70064 -- | STOOL                                                    |   9291 |  26427 |     78
    , 70014 -- | BLOOD CULTURE - NEONATE                                  |   6580 |  10032 |   1850
    , 70023 -- | CATHETER TIP-IV                                          |   5518 |  21216 |  11241
    , 70070 -- | SWAB                                                     |   5220 |  33623 |  24283
    , 70017 -- | SEROLOGY/BLOOD                                           |   3568 |   4853 |      0
    , 70011 -- | BLOOD CULTURE ( MYCO/F LYTIC BOTTLE)                     |   2733 |   6638 |    869
    , 70081 -- | URINE                                                    |   2622 |   3018 |      0
    , 70026 -- | CSF;SPINAL FLUID                                         |   2508 |   5526 |   1004
    , 70021 -- | BRONCHOALVEOLAR LAVAGE                                   |   2391 |  11613 |   7450
    , 70054 -- | PLEURAL FLUID                                            |   1694 |   4110 |   1550
    , 70076 -- | TISSUE                                                   |   1619 |   9142 |   6249
    , 70053 -- | PERITONEAL FLUID                                         |   1259 |   5982 |   3392
    , 70057 -- | Rapid Respiratory Viral Screen & Culture                 |   1144 |   1515 |      0
    , 70046 -- | IMMUNOLOGY                                               |   1101 |   1579 |      0
    , 70051 -- | FLUID,OTHER                                              |   1003 |   4572 |   3135
    , 70045 -- | Immunology (CMV)                                         |    909 |   1818 |      0
    , 70013 -- | FLUID RECEIVED IN BLOOD CULTURE BOTTLES                  |    902 |   2358 |    836
    , 70087 -- | Blood (CMV AB)                                           |    828 |    879 |      0
    , 70042 -- | Influenza A/B by DFA                                     |    810 |    915 |      0
    , 70088 -- | Blood (EBV)                                              |    786 |    824 |      0
    , 70069 -- | SWAB                                                     |    674 |   1662 |    934
    , 70059 -- | Staph aureus Screen                                      |    631 |   1428 |    845
    , 70003 -- | ABSCESS                                                  |    591 |   4875 |   3872
    , 70022 -- | BRONCHIAL WASHINGS                                       |    501 |   2215 |   1537
    , 70067 -- | SWAB                                                     |    434 |   2298 |   1695
    , 70009 -- | BILE                                                     |    392 |   3549 |   2883
    , 70093 -- | Blood (Toxo)                                             |    377 |    402 |      0
    , 70047 -- | JOINT FLUID                                              |    360 |   1030 |    582
    , 70090 -- | Mini-BAL                                                 |    351 |   1319 |    911
    , 70005 -- | ASPIRATE                                                 |    330 |    828 |    439
    , 70019 -- | BONE MARROW - CYTOGENETICS                               |    273 |    372 |      0
    , 70034 -- | FOREIGN BODY                                             |    178 |    760 |    566
    , 70028 -- | Direct Antigen Test for Herpes Simplex Virus Types 1 & 2 |    171 |    189 |      0
    , 70052 -- | PERIPHERAL BLOOD LYMPHOCYTES                             |    159 |    164 |      0
    , 70068 -- | SWAB                                                     |    122 |    233 |     96
    , 70002 -- | THROAT FOR STREP                                         |    120 |    143 |     15
    , 70075 -- | THROAT CULTURE                                           |    103 |    165 |     35
    , 70030 -- | DIRECT ANTIGEN TEST FOR VARICELLA-ZOSTER VIRUS           |    101 |    107 |      0
    , 70077 -- | URINE                                                    |     92 |     95 |      0
    , 70061 -- | SKIN SCRAPINGS                                           |     91 |    104 |      7
    , 70037 -- | FOOT CULTURE                                             |     90 |    743 |    589
    , 70041 -- | VIRAL CULTURE:R/O HERPES SIMPLEX VIRUS                   |     79 |    106 |      0
    , 70029 -- | DIALYSIS FLUID                                           |     77 |    215 |     42
    , 70066 -- | STOOL (RECEIVED IN TRANSPORT SYSTEM)                     |     77 |     94 |      0
    , 70033 -- | EYE                                                      |     76 |    408 |    289
    , 70018 -- | BONE MARROW                                              |     73 |     85 |      5
    , 70040 -- | SWAB                                                     |     64 |     70 |      0
    , 70060 -- | Stem Cell - Blood Culture                                |     62 |    161 |      0
    , 70010 -- | BIOPSY                                                   |     62 |    147 |     74
    , 70049 -- | NEOPLASTIC BLOOD                                         |     50 |     55 |      0
    , 70036 -- | FLUID WOUND                                              |     33 |    239 |    191
    , 70024 -- | VIRAL CULTURE: R/O CYTOMEGALOVIRUS                       |     33 |     37 |      0
    , 70058 -- | RAPID RESPIRATORY VIRAL ANTIGEN TEST                     |     29 |     34 |      6
    , 70043 -- | Influenza A/B by DFA - Bronch Lavage                     |     29 |     32 |      0
    , 70035 -- | FLUID,OTHER                                              |     27 |     33 |      0
    , 70080 -- | URINE,KIDNEY                                             |     26 |    371 |    350
    -- , 70055 -- | POSTMORTEM CULTURE                                       |     22 |     76 |      0
    , 70020 -- | BRONCHIAL BRUSH                                          |     21 |     36 |      8
    , 70031 -- | EAR                                                      |     19 |    101 |     63
    , 70008 -- | BRONCHIAL BRUSH - PROTECTED                              |     17 |     20 |      0
    , 70086 -- | XXX                                                      |     16 |     23 |     15
    , 70089 -- | Blood (Malaria)                                          |     13 |     15 |      0
    , 70072 -- | TRACHEAL ASPIRATE                                        |     12 |     63 |     50
    , 70038 -- | FECAL SWAB                                               |     12 |     26 |     15
    , 70085 -- | WORM                                                     |     11 |     11 |      0
    , 70082 -- | URINE,SUPRAPUBIC ASPIRATE                                |     10 |     41 |     32
    , 70025 -- | CRE Screen                                               |     10 |     11 |      0
    , 70063 -- | STERILITY CULTURE                                        |      9 |     49 |     36
    , 70073 -- | TISSUE                                                   |      9 |      9 |      0
    , 70092 -- | SWAB, R/O GC                                             |      9 |      9 |      0
    , 70083 -- | VARICELLA-ZOSTER CULTURE                                 |      7 |      8 |      0
    , 70032 -- | Blood (EBV)                                              |      7 |      7 |      0
    , 70084 -- | SWAB                                                     |      5 |      9 |      0
    , 70027 -- | CORNEAL EYE SCRAPINGS                                    |      4 |     18 |     15
    , 70074 -- | THROAT                                                   |      4 |      4 |      0
    -- , 70016 -- | BLOOD CULTURE (POST-MORTEM)                              |      3 |     16 |      0
    , 70004 -- | ARTHROPOD                                                |      3 |      3 |      0
    , 70065 -- | SCOTCH TAPE PREP/PADDLE                                  |      3 |      3 |      0
    , 70050 -- | NOSE                                                     |      2 |     10 |      9
    , 70071 -- | SWAB - R/O YEAST                                         |      2 |      2 |      0
    , 70056 -- | RECTAL - R/O GC                                          |      2 |      2 |      0
    , 70039 -- | GASTRIC ASPIRATE                                         |      2 |      2 |      0
    , 70048 -- | NAIL SCRAPINGS                                           |      2 |      2 |      0
    , 70078 -- | URINE,PROSTATIC MASSAGE                                  |      2 |      2 |      0
    , 70006 -- | ANORECTAL/VAGINAL CULTURE                                |      2 |      2 |      0
    , 70015 -- | BLOOD                                                    |      2 |      2 |      0
    , 70007 -- | BLOOD BAG FLUID                                          |      1 |      1 |      0
    , 70044 -- | Influenza A/B by DFA - Bronch Wash                       |      1 |      1 |      0
  )
  group by me.hadm_id, chartdate, charttime, spec_type_desc
) t1
where t1.rn = 1;
