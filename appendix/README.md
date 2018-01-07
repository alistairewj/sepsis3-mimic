# Appendix

The folder contains notebooks pertaining to a number of analyses run using the septic cohort.


# Building an MFP model using R

(Note: this section is incomplete).

The original Sepsis-3 publication built a fractional polynomial regression model using various covariates and SOFA/SIRS/qSOFA. Unfortunately, there wasn't a package in Python which could build the fractional polynomial regression model. The package used was available in R, so we use a subprocess in python to call R. This step is optional as most of the code will run without R - if these packages not installed then one of the cells will print `RScript returned error status 127.` a few times. The rest of the code will work however.

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
