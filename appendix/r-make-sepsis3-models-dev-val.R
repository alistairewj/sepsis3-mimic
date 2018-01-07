#!/usr/bin/env Rscript
library(mfp)
args = commandArgs(trailingOnly=TRUE)

if (length(args)==0) {
  stop("At least one argument must be supplied (input file).n", call.=FALSE)
}

# load the data
sep3 <- read.table(paste(args[1], '-dev.csv', sep=""), header=TRUE, sep=",")
sep3_val <- read.table(paste(args[1], '-val.csv', sep=""), header=TRUE, sep=",")

# base formula for the model
formula = "hospital_expire_flag ~ fp(age) + fp(elixhauser_hospital) + is_male + race_black + race_other"

# if input - use the formula provided
if (length(args)==3) {
formula = args[3]
}

# parse the target from the formula
target_header = strsplit(formula, " ~", fixed = TRUE)
target_header = target_header[[1]][1]

# build the model
mod.mfp <- mfp(as.formula(formula),data=sep3,family="binomial",verbose=FALSE)

# output model coefficients and standard errors
print('Summary for MFP model defined by the following formula:')
print(formula)
print(summary(mod.mfp))

# output a text file of the predictions
preds <- predict(mod.mfp,type="response")
write.csv(preds,paste(args[2], '-dev.csv', sep=""),row.names=FALSE)
write.csv(sep3[target_header],paste(args[2], '-dev-tar.csv', sep=""),row.names=FALSE)

preds <- predict(mod.mfp,sep3_val,type="response")
write.csv(preds,paste(args[2], '-val.csv', sep=""),row.names=FALSE)
write.csv(sep3_val[target_header],paste(args[2], '-val-tar.csv', sep=""),row.names=FALSE)
