#!/usr/bin/env Rscript
library(mfp)
args = commandArgs(trailingOnly=TRUE)

if (length(args)==0) {
  stop("At least one argument must be supplied (input file).n", call.=FALSE)
}

# load the data
sep3 <- read.table(args[1], header=TRUE, sep=",")

# base formula for the model
formula = "~ fp(age) + fp(elixhauser_hospital) + is_male + race_black + race_other"

# add in the target header, if available
if (length(args)==3) {
# we also specify the target
formula = paste(args[3], formula, sep=" ")
} else {
formula = paste('hospital_expire_flag', formula, sep=" ")
}
# add in additional covariate (4th argument)
if (length(args)==4) {
formula = paste(formula, args[4], sep=" + ")
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
