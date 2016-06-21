#!/usr/bin/env Rscript
library(mfp)
args = commandArgs(trailingOnly=TRUE)

if (length(args)==0) {
  stop("At least one argument must be supplied (input file).n", call.=FALSE)
}

# load the data
sep3 <- read.table(args[1], header=TRUE, sep=",")

# build the model
formula = "hospital_expire_flag~fp(age) + fp(elixhauser_hospital) + is_male + race_black + race_other"
if (length(args)==3) {
# we have an additional covariate to add
formula = paste(formula, args[3], sep=" + ")
}
print(formula)
mod.mfp <- mfp(as.formula(formula),data=sep3,family="binomial",verbose=FALSE)

# output a text file of the predictions
preds <- predict(mod.mfp,type="response")
write.csv(preds,args[2],row.names=FALSE)

# output a text file which reads:
# variable name, exponent, coefficient
#? best way to do this?
# mod.mfp$formula
# mod.mfp$coef
