# sepsis3-mimic
Evaluation of the Sepsis-3 guidelines in MIMIC-III

# Using this repository

The main body of code is broken down into three files:

* sepsis-3-get-data.ipynb - this exports the data from the database and writes it to a CSV file
* sepsis-3-hospital-mortality.ipynb - using the CSV files, this analyzes the data using hospital mortality as the outcome of interest
* sepsis-3-angus.ipynb - using the CSV files, this analyzes the data using sepsis as defined by Angus et al. as the outcome of interest

Before these notebooks can be run, there are a number of prerequisites:

1. PostgreSQL version 9.4 or later
2. The MIMIC-III database installed in PostgreSQL
3. Python with the `numpy`, `pandas`, `matplotlib`, `psycoph2`, `statsmodels` and `sklearn` packages
4. (Optional) In order to run the multifractional polynomial, both R and the `mfp` package for R are required.
5. SQL scripts to generate materialized views must be executed

To facilitate use of this repository, we'll go over brief installation steps. Detail is provided for the Ubuntu 16.04 operating system - if you can figure out how to accomplish each step in your own operating system, we would welcome a guide!

## Install packages and database

Unless otherwise specified, commands in the code blocks that follow are run from the terminal.

### Install PostgreSQL

First, a working version of PostgreSQL is needed. Ubuntu usually comes with the necessary version of PostgreSQL, so we can simply check the version of PostgreSQL that is installed:

```sh
psql --version
```

This returned `psql (PostgreSQL) 9.5.4` for me. You'll need at least version 9.4 as that's when materialized views became available in Postgres. If it's not installed, you can install it in Ubuntu with:

```sh
sudo apt-get install postgresql
```

Just make sure it's at least version 9.4.

### Install MIMIC-III

MIMIC-III is an openly available database sourced from the Beth Israel Deaconess Medical Center in Boston, MA, USA. Access to MIMIC requires signing of a data use agreement - you can find details on how to acquire the data here: http://mimic.physionet.org/gettingstarted/dbsetup/

After you have acquired the data files (a set of plaintext .csv files), follow the instructions to import MIMIC into a local Postgres database here (Mac/Unix): http://mimic.physionet.org/tutorials/install-mimic-locally-ubuntu/

There are instructions for Windows users as well, found here: http://mimic.physionet.org/tutorials/install-mimic-locally-windows/

### Install Python with various packages

Most of the packages used in this repository are available via Ubuntu's software management system, and can be installed as follows:

```
sudo apt-get install python python-dev python-pip python-numpy python-pandas python-scipy python-matplotlib python-sklearn python-statsmodels
```

Alternatively, if you prefer to use Python's package manager (`pip`), and already have it installed, you can run the following from the root directory of this repository:

```
pip install -r requirements.txt
```

### Install R and necessary package

Unfortunately, there wasn't a package in Python which could build the fractional polynomial regression model. The package used available in R instead. This step is optional as most of the code will run without R - if these packages not installed then one of the cells will print `RScript returned error status 127.` a few times. The rest of the code will work however.

R can be installed as follows:

```
sudo apt-get install r-base r-base-dev
```

Then, install the necessary `mfp` package by using one of two methods:

(1) Running the following from the command line:


```
wget https://cran.r-project.org/src/contrib/mfp_1.5.2.tar.gz
sudo R CMD INSTALL mfp_1.5.2.tar.gz
```

or (2) Running R and, in the R prompt, calling:

```R
install.packages("mfp")
```

## Check it's working

You should have a working version of MIMIC on your local computer now. The following commands should launch `psql`, a command line application for querying the database, and the subsequent commands should return 5 rows of data.

```
psql
\c mimic;
set search_path to mimiciii;
select * from icustays limit 5;
```

## Clone this repository

You will need a local copy of the code in this repository. The easiest way to acquire this is to use `git` to clone the data locally. First install `git`:

```
sudo apt-get install git
```

Ensure to clone the repository with the `--recursive` flag, as it relies on a distinct repository (mimic-code):

```
git clone https://github.com/alistairewj/sepsis3-mimic sepsis3-mimic --recursive
```

If you already have the repository cloned on your local computer, but you didn't use the `--recursive` flag, you can add it back quite easily:

```
cd sepsis3-mimic
git submodule update --init --recursive
```

## Run SQL scripts to generate views

Change to the directory with the queries and run the main SQL script through `psql`:

```
cd query
psql
\i make-tables.sql
```

This will start the generation of all the tables - which can take about an hour. You may see a lot of `NOTICE` warnings: don't worry about them. The query logic is "check if the table exists, and if it does, drop it". These warnings indicate that the table did not exist (and nor would you expect it to on a fresh install!).
