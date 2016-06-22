# Data extraction

The entire data extraction can be run by calling the `make-tables.sql` script.
This script calls all the necessary SQL scripts in the correct order and generates the final view of the data: sepsis3.

There is an additional view, `sepsis3-cohort`, which defines the inclusion/exclusion criteria applied.

## Details

1. Get time of suspicion of infection
2. Create sepsis3-cohort view with this info
3. Create all the severity scores using data centered around infection time ([-24, 24] hours)
4. Create final table
