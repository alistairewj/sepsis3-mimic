# Data extraction

The entire data extraction can be run by calling the `make-tables.sql` script.
This script calls all the necessary SQL scripts in the correct order and generates the final view of the data: sepsis3.

There is an additional view, `sepsis3-cohort`, which defines the inclusion/exclusion criteria applied.

## Details

0. `suspicion-of-infection.sql` - define patients suspected of infection
1. `cohort.sql` - Create a cohort applying exclusion criteria: no CSURG, no neonates, no readmissions
2. Create all the severity scores using data centered around infection time ([-24, 24] hours)
3. `sepsis3.sql` - Get data for the patients with suspected infection on the first day of their ICU admission

## TODO:

* Venn diagram of SOFA >= 2, Angus, Martin (write XX% of patients were not suspected in legend)
* Mortality rate for above groups, composite outcome rate for groups
* performance of prediction model (1) with just SOFA, (2) with SOFA+lactate+comorbid burden - discussion: there is room for improvement in the criteria


### sensitivity analysis

* crosstab of suspected infection and SIRS as a sensitivity analysis
* ?chart review 100 patients to verify that they were admitted to the ICU because of sepsis/concerns around sepsis?
* sensitivity analysis: assign higher organ failure if comorbid codes met (renal failure, resp failure, ??)

### extract data for first 24 hours of patient's stay
### how well does SOFA >= 2 and Angus criteria correlate?

    | Angus | Explicit  | Martin
PPV |  70.7 | 100       | 97.6
NPV |  91.5 | 86.0      | 87.0
Se  |  50.3 | 9.3       | 16.8
Sp  |  96.3 | 100       | 99.9

Angus had 50% sensitivity and 71% PPV - lower PPV than others, but much higher sensitivity

other systems

Martin definition: 038 (septicemia), 020.0 (septicemic), 790.7 (bacteremia), 117.9 (disseminated fungal infection), 112.5 (disseminated candida infection), and 112.81 (disseminated fungal endocarditis)
 - Martin GS, Mannino DM, Eaton S, Moss M. The Epidemiology of Sepsis in the United States from 1979 through 2000. New England Journal of Medicine. 2003; 348:1546–54. [PubMed: 12700374]


038 had ppv of 88.9% and NPV of 80%
the 038-centric definition—focused on hematogenous spread of microorganisms—poorly aligns with contemporary clinical practice for severe sepsis as it may inappropriately exclude non- bacteremic patients.

severe sepsis (995.92) or septic shock (785.52)
in this study: 100% PPV, 9.3% sens, 100% specificity
super pure cohort

single center - 995.92 had 52% sens and 98% spec
another, 785.52 had 52% sens and 98% spec, (46%, 99%) in another study

### long-term outcomes?

http://www.sciencedirect.com/science/article/pii/S1473309917301172

implies qSOFA>SOFA>SIRS for predicting bad long term outcome, even though SIRS>SOFA>qSOFA for identifying infection.

### clinical definition better than billing codes?

https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4743875/
they used old definition (SIRS) but showed disagreement among new/old definition

### how does lactate work?
