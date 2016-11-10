#!/usr/bin/env Rscript
library(mfp)
args = commandArgs(trailingOnly=TRUE)

if (length(args)==0) {
  stop("At least one argument must be supplied (input file).n", call.=FALSE)
}

# load the data
sep3 <- read.table(args[1], header=TRUE, sep=",")

# base formula for the model
formula = "hospital_expire_flag ~ fp(age) + fp(elixhauser_hospital) + is_male + race_black + race_other"

# if input - use the formula provided
if (length(args)==3) {
formula = args[3]
}

# build the model
mod.mfp <- mfp(as.formula(formula),data=sep3,family="binomial",verbose=FALSE)

# output model coefficients and standard errors
print('Summary for MFP model defined by the following formula:')
print(formula)
print(summary(mod.mfp))

# output a text file of the predictions
preds <- predict(mod.mfp,type="response")
write.csv(preds,args[2],row.names=FALSE)
