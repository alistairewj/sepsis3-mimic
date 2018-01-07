from __future__ import print_function

import sys
import os
import psycopg2
import pandas as pd
import numpy as np
import subprocess

# we use ordered dictionaries to ensure consistent output order
from collections import OrderedDict

# modules needed for venn diagrams
import matplotlib.pyplot as plt
from matplotlib_venn import venn3

from . import roc_utils as ru

from statsmodels.formula.api import logit

from sklearn import metrics
import scipy.stats

def print_cm(y, yhat, header1='y', header2='yhat'):
    print('\nConfusion matrix')
    cm = metrics.confusion_matrix(y, yhat)
    TN = cm[0,0]
    FP = cm[0,1]
    FN = cm[1,0]
    TP = cm[1,1]
    N = TN+FP+FN+TP
    print('      \t{:6s}\t{:6s}'.format(header1 + '=0', header1 + '=1'))
    print('{:6s}\t{:6g}\t{:6g}\tNPV={:2.2f}'.format(header2 + '=0', cm[0,0],cm[1,0], 100.0*TN / (TN+FN))) # NPV
    print('{:6s}\t{:6g}\t{:6g}\tPPV={:2.2f}'.format(header2 + '=1', cm[0,1],cm[1,1], 100.0*TP / (TP+FP))) # PPV
    # add sensitivity/specificity as the bottom line
    print('   \t{:2.2f}\t{:2.2f}\tAcc={:2.2f}'.format(100.0*TN/(TN+FP), 100.0*TP/(TP+FN), 100.0*(TP+TN)/N))
    print('   \tSpec\tSens')

def get_op_stats(yhat_dict, y):
    # for a given set of predictions, prints a table of the performances
    # yhat_all should be a dictionary containing numpy arrays of length N
    # y is a length N numpy array

    yhat_names=yhat_dict.keys()

    stats_names = [ 'TN','FP','FN','TP','Sens','Spec','PPV','NPV','F1','NTP','NFP']
    stats_all = OrderedDict()

    for i, yhat_name in enumerate(yhat_dict):
        stats = dict()
        yhat = yhat_dict[yhat_name]

        cm = metrics.confusion_matrix(y, yhat)

        # confusion matrix is output as int64 - we'd like to calculate percentages
        cm = cm.astype(float)
        # to make the code clearer, extract components from confusion matrix
        TN = cm[0,0] # true negatives
        FP = cm[0,1] # false positives
        FN = cm[1,0] # false negatives
        TP = cm[1,1] # true positives

        stats['sens'] = 100.0*TP/(TP+FN) # Sensitivity
        stats['spec'] = 100.0*TN/(TN+FP) # Specificity
        stats['ppv'] = 100.0*TP/(TP+FP) # PPV
        stats['npv'] = 100.0*TN/(TN+FN) # NPV

        # F1, the harmonic mean of PPV/Sensitivity
        stats['f1'] = 2.0*(stats['sens'] * stats['ppv']) / (stats['ppv'] + stats['sens'])

        # NTP/100: 100 patients * % outcome * (ppv)
        stats['ntp'] = 100.0 * (TP+FP)/(TP+FP+TN+FN) * (stats['ppv']/100.0)
        # NFP/100: 100 patients * % outcome * (1-ppv)
        stats['nfp'] = 100.0 * (TP+FP)/(TP+FP+TN+FN) * (1-stats['ppv']/100.0)

        #stats_all[i,11] = (TP/FP)/(FN/TN) # diagnostic odds ratio

        # now push the stats to the final stats vector
        stats['tn'] = TN
        stats['fp'] = FP
        stats['fn'] = FN
        stats['tp'] = TP

        # add the dictionary to the top of the ordered dict
        stats_all.update({yhat_name: stats})
    return stats_all


def print_op_stats(stats_all):
    stats_names = [ 'TN','FP','FN','TP','Sens','Spec','PPV','NPV','F1','NTP','NFP']

    # calculate confidence intervals
    ci = dict()

    for i, yhat_name in enumerate(stats_all):
        stats = stats_all[yhat_name]
        TN = stats['tn']
        FP = stats['fp']
        FN = stats['fn']
        TP = stats['tp']

        # add the CI
        ci[yhat_name] = dict()
        ci[yhat_name]['sens'] = binomial_proportion_ci(TP, TP+FN, alpha = 0.05)
        ci[yhat_name]['spec'] = binomial_proportion_ci(TN, TN+FP, alpha = 0.05)
        ci[yhat_name]['ppv'] = binomial_proportion_ci(TP, TP+FP, alpha = 0.05)
        ci[yhat_name]['npv'] = binomial_proportion_ci(TN, TN+FN, alpha = 0.05)

    print('Metric')

    # print the names of the predictions, if they were provided
    print('') # newline
    print('{:5s}'.format(''),end='') # spacing
    for i, yhat_name in enumerate(stats_all):
        print('\t{:8s}'.format(yhat_name), end='')
    print('') # newline

    # print the stats calculated
    for n, stats_name_pretty in enumerate(stats_names):
        # the dictionary uses all lower case
        stats_name = stats_name_pretty.lower()

        print('{:5s}'.format(stats_name_pretty), end='')
        for i, yhat_name in enumerate(stats_all):
            stats = stats_all[yhat_name]
            if stats_name not in stats:
                print('\t{:8s}'.format(''), end='')
            elif stats_name in ['tp','fp','tn','fn']:
                if i>0:
                    # extra spacing
                    print('',end='\t')
                print('\t{:5.0f}'.format(stats[stats_name]), end='')
            elif stats_name in ['sens','spec','ppv','npv']: # print sensitivity, specificity, etc with CI
                print('\t{:2.0f} [{:2.0f}, {:2.0f}]'.format(stats[stats_name],
                ci[yhat_name][stats_name][0]*100,ci[yhat_name][stats_name][1]*100),end='')
            else: # use decimal format for the rest
                print('\t {:3.2f}{:3s}'.format(stats[stats_name],''), end='')

        print('') # newline

    return None

def print_stats_to_file(filename, yhat_names, stats_all):
    # print the table to a file for convenient viewing
    f = open(filename,'w')
    stats_names = [ 'TN','FP','FN','TP','N','Sens','Spec','PPV','NPV','F1','NTP','NFP']

    # derive CIs
    ci = np.zeros( [stats_all.shape[0], stats_all.shape[1], 2] )
    for i in range(stats_all.shape[0]):
        # add the CI
        TN = stats_all[i,0]
        FP = stats_all[i,1]
        FN = stats_all[i,2]
        TP = stats_all[i,3]

        ci[i,4,:] = binomial_proportion_ci(TP, TP+FN, alpha = 0.05)
        ci[i,5,:] = binomial_proportion_ci(TN, TN+FP, alpha = 0.05)
        ci[i,6,:] = binomial_proportion_ci(TP, TP+FP, alpha = 0.05)
        ci[i,7,:] = binomial_proportion_ci(TN, TN+FN, alpha = 0.05)

    f.write('Subgroup')
    for n, stats_name in enumerate(stats_names):
        f.write('\t%s' % stats_name)

    f.write('\n')

    for i, yhat_name in enumerate(yhat_names):
        f.write('%s' % yhat_name)

        for n, stats_name in enumerate(stats_names):
            if n < 5: # use integer format for the tp/fp
                f.write('\t%10.0f' % stats_all[i,n])
            elif n < 8: # print sensitivity, specificity, etc with CI
                f.write('\t%4.2f [{:2.2f}, {:2.2f}]' % stats_all[i,n], ci[i,n,0], ci[i,n,1])
            else: # use decimal format for the sensitivity, specificity, etc
                f.write('\t%10.2f' % stats_all[i,n])

        f.write('\n') # newline

    f.close()

def print_demographics(df, idx=None):
    # create a dictionary which maps each variable to a data type
    all_vars = OrderedDict((
    ('N', 'N'),
    ('age', 'median'),
    ('gender', 'gender'),
    ('bmi', 'continuous'),
    ('ethnicity', 'race'),
    ('elixhauser_hospital', 'median'),
    ('qsofa', 'median'),
    ('sirs', 'median'),
    ('sofa', 'median'),
    ('mlods', 'median'),
    ('lactate_max', 'continuous'),
    ('vent', 'binary'),
    ('icu_los', 'median'),
    ('hosp_los', 'median'),
    ('thirtyday_expire_flag', 'binary'),
    ('hospital_expire_flag', 'binary')))

    if idx is None:
        # print demographics for entire dataset
        for i, curr_var in enumerate(all_vars):
            if all_vars[curr_var] == 'N': # print number of patients
                print('{:20s}\t{:4g}'.format(curr_var, df.shape[0]))
            elif curr_var in df.columns:
                if all_vars[curr_var] == 'continuous': # report mean +- STD
                    print('{:20s}\t{:2.1f} +- {:2.1f}'.format(curr_var, df[curr_var].mean(), df[curr_var].std()))
                elif all_vars[curr_var] == 'gender': # convert from M/F
                    print('{:20s}\t{:4g} ({:2.1f}%)'.format(curr_var, np.sum(df[curr_var].values=='M'),
                    100.0*np.sum(df[curr_var].values=='M').astype(float) / df.shape[0]))
                # binary, report percentage
                elif all_vars[curr_var] == 'binary':
                    print('{:20s}\t{:4g} ({:2.1f}%)'.format(curr_var, df[curr_var].sum(),
                    100.0*(df[curr_var].mean()).astype(float)))
                # report median [25th percentile, 75th percentile]
                elif all_vars[curr_var] == 'median':
                    print('{:20s}\t{:2.1f} [{:2.1f}, {:2.1f}]'.format(curr_var, df[curr_var].median(),
                    np.percentile(df[curr_var].values,25,interpolation='midpoint'), np.percentile(df[curr_var].values,75,interpolation='midpoint')))
                elif all_vars[curr_var] == 'measured':
                    print('{:20s}\t{:2.1f}%'.format(curr_var, 100.0*np.mean(df[curr_var].isnull())))
                elif all_vars[curr_var] == 'race':
                    # special case: print each race individually
                    # race_black, race_other
                    print('{:20s}\t'.format('Race'))

                    # each component
                    curr_var_tmp = 'White'
                    print('{:20s}\t{:4g} ({:2.1f}%)'.format(curr_var_tmp, df['race_white'].sum(),
                    100.0*(df['race_white'].mean()).astype(float)))
                    curr_var_tmp = 'Black'
                    print('{:20s}\t{:4g} ({:2.1f}%)'.format(curr_var_tmp, df['race_black'].sum(),
                    100.0*(df['race_black'].mean()).astype(float)))
                    curr_var_tmp = 'Hispanic'
                    print('{:20s}\t{:4g} ({:2.1f}%)'.format(curr_var_tmp, df['race_hispanic'].sum(),
                    100.0*(df['race_black'].mean()).astype(float)))
                    # curr_var_tmp = 'Other'
                    # print('{:20s}\t{:4g} ({:2.1f}%)'.format(curr_var_tmp, df['race_other'].sum(),
                    # 100.0*(df['race_other'].mean()).astype(float)))

                # additional lactate measurements output with lactate_max
                if curr_var == 'lactate_max':
                    # also print measured
                    print('{:20s}\t{:4g} ({:2.1f}%)'.format(curr_var.replace('_max',' ') + 'measured',
                    np.sum(~df[curr_var].isnull()),100.0*np.mean(~df[curr_var].isnull())))
                    print('{:20s}\t{:4g} ({:2.1f}%)'.format(curr_var.replace('_max',' ') + '> 2',
                    np.sum(df[curr_var] >= 2),100.0*np.mean(df[curr_var] >= 2)))

            else:
                print('{:20s}'.format(curr_var))
    else:
        # print demographics split into two groups
        # also print p-values testing between the two groups
        for i, curr_var in enumerate(all_vars):
            if all_vars[curr_var] == 'N': # print number of patients
                print('{:20s}\t{:4g}{:5s}\t{:4g}{:5s}\t{:5s}'.format(curr_var,
                np.sum(~idx), '',
                np.sum(idx), '',
                ''))
            elif curr_var in df.columns:
                if all_vars[curr_var] == 'continuous': # report mean +- STD
                    tbl = np.array([ [df[~idx][curr_var].mean(), df[idx][curr_var].mean()],
                    [df.loc[~idx,curr_var].std(), df.loc[idx,curr_var].std()]])

                    stat, pvalue = scipy.stats.ttest_ind(df[~idx][curr_var], df[idx][curr_var],
                    equal_var=False, nan_policy='omit')

                    # print out < 0.001 if it's a very low p-value
                    if pvalue < 0.001:
                        pvalue = '< 0.001'
                    else:
                        pvalue = '{:0.3f}'.format(pvalue)

                    print('{:20s}\t{:2.1f} +- {:2.1f}\t{:2.1f} +- {:2.1f}\t{:5s}'.format(curr_var,
                    tbl[0,0], tbl[1,0],
                    tbl[0,1], tbl[1,1],
                    pvalue))

                elif all_vars[curr_var] in ('gender','binary'): # convert from M/F
                    # build the contingency table
                    if all_vars[curr_var] == 'gender':
                        tbl = np.array([ [np.sum(df[~idx][curr_var].values=='M'), np.sum(df[idx][curr_var].values=='M')],
                        [np.sum(df[~idx][curr_var].values!='M'), np.sum(df[idx][curr_var].values!='M')] ])
                    else:
                        tbl = np.array([ [np.sum(df[~idx][curr_var].values), np.sum(df[idx][curr_var].values)],
                        [np.sum(1 - df[~idx][curr_var].values), np.sum(1 - df[idx][curr_var].values)] ])


                    # get the p-value
                    chi2, pvalue, dof, ex = scipy.stats.chi2_contingency( tbl )

                    # print out < 0.001 if it's a very low p-value
                    if pvalue < 0.001:
                        pvalue = '< 0.001'
                    else:
                        pvalue = '{:0.3f}'.format(pvalue)

                    # binary, report percentage
                    print('{:20s}\t{:4g} ({:2.1f}%)\t{:4g} ({:2.1f}%)\t{:5s}'.format(curr_var,
                    tbl[0,0], 100.0*tbl[0,0].astype(float) / (tbl[0,0]+tbl[1,0]),
                    tbl[0,1],
                    100.0*tbl[0,1].astype(float) / (tbl[0,1]+tbl[1,1]),
                    pvalue))

                elif all_vars[curr_var] == 'median':
                    stat, pvalue = scipy.stats.mannwhitneyu(df[~idx][curr_var],
                    df[idx][curr_var],
                    use_continuity=True, alternative='two-sided')

                    # print out < 0.001 if it's a very low p-value
                    if pvalue < 0.001:
                        pvalue = '< 0.001'
                    else:
                        pvalue = '{:0.3f}'.format(pvalue)

                    print('{:20s}\t{:2.1f} [{:2.1f}, {:2.1f}]\t{:2.1f} [{:2.1f}, {:2.1f}]\t{:5s}'.format(curr_var,
                    df[~idx][curr_var].median(), np.percentile(df[~idx][curr_var].values,25,interpolation='midpoint'), np.percentile(df[~idx][curr_var].values,75,interpolation='midpoint'),
                    df[idx][curr_var].median(), np.percentile(df[idx][curr_var].values,25,interpolation='midpoint'), np.percentile(df[idx][curr_var].values,75,interpolation='midpoint'),
                    pvalue))

                elif all_vars[curr_var] == 'measured':
                    # build the contingency table
                    tbl = np.array([ [np.sum(df[~idx][curr_var].isnull()), np.sum(df[idx][curr_var].isnull())],
                    [np.sum(~df[~idx][curr_var].isnull()), np.sum(~df[idx][curr_var].isnull())] ])

                    # get the p-value
                    chi2, pvalue, dof, ex = scipy.stats.chi2_contingency( tbl )

                    # print out < 0.001 if it's a very low p-value
                    if pvalue < 0.001:
                        pvalue = '< 0.001'
                    else:
                        pvalue = '{:0.3f}'.format(pvalue)

                    print('{:20s}\t{:2.1f}%\t{:2.1f}%'.format(curr_var,
                    np.sum(~df[~idx][curr_var].isnull()),
                    100.0*np.mean(~df[~idx][curr_var].isnull()),
                    np.sum(~df[idx][curr_var].isnull()),
                    100.0*np.mean(~df[idx][curr_var].isnull()),
                    pvalue))

                elif all_vars[curr_var] == 'race':
                    # special case: evaluate each race in chi2
                    # race_black, race_other

                    # create a contingency table with three rows

                    # use crosstab
                    df['race'] = 'other'
                    df.loc[df['race_black']==1,'race'] = 'black'
                    df.loc[df['race_white']==1,'race'] = 'white'
                    df.loc[df['race_hispanic']==1,'race'] = 'hispanic'
                    tbl = pd.crosstab(df.race, idx, margins = True)

                    curr_var_vec = tbl.index.values[0:-1]
                    # Extract table without totals
                    tbl = tbl.ix[0:-1,0:-1]

                    # get the p-value
                    chi2, pvalue, dof, ex = scipy.stats.chi2_contingency( tbl, correction=False )

                    # print out < 0.001 if it's a very low p-value
                    if pvalue < 0.001:
                        pvalue = '< 0.001'
                    else:
                        pvalue = '{:0.3f}'.format(pvalue)

                    # first print out we are comparing races (with p-value)
                    print('{:20s}\t{:10s}\t{:10s}\t{:5s}'.format(curr_var,'','',pvalue))

                    # next print out individual race #s (no p-value)
                    for r in curr_var_vec:
                        print('{:20s}\t{:4g} ({:2.1f}%)\t{:4g} ({:2.1f}%)\t{:5s}'.format('  ' + r,
                        tbl.loc[r,False], 100.0*tbl.loc[r,False].astype(float) / np.sum(tbl.loc[:,False]),
                        tbl.loc[r, True], 100.0*tbl.loc[r, True].astype(float) / np.sum(tbl.loc[:, True]),
                        '')) # no individual p-value

                # additional lactate measurements output with lactate_max
                if curr_var == 'lactate_max':
                    # for lactate, we print two additional rows:
                    # 1) was lactate ever measured?
                    # 2) was lactate ever > 2 ?

                    # measured...
                    # build the contingency table
                    tbl = np.array([ [np.sum(df[~idx][curr_var].isnull()), np.sum(df[idx][curr_var].isnull())],
                    [np.sum(~df[~idx][curr_var].isnull()), np.sum(~df[idx][curr_var].isnull())] ])

                    # get the p-value
                    chi2, pvalue, dof, ex = scipy.stats.chi2_contingency( tbl )

                    # print out < 0.001 if it's a very low p-value
                    if pvalue < 0.001:
                        pvalue = '< 0.001'
                    else:
                        pvalue = '{:0.3f}'.format(pvalue)

                    print('{:20s}\t{:4g} ({:2.1f}%)\t{:4g} ({:2.1f}%)\t{:5s}'.format(curr_var.replace('_max',' ') + 'measured',
                    np.sum(~df[~idx][curr_var].isnull()),
                    100.0*np.mean(~df[~idx][curr_var].isnull()),
                    np.sum(~df[idx][curr_var].isnull()),
                    100.0*np.mean(~df[idx][curr_var].isnull()),
                    pvalue))


                    # value > 2...
                    # build the contingency table
                    tbl = np.array([ [np.sum(df[~idx][curr_var] >= 2), np.sum(df[idx][curr_var] >= 2)],
                    [np.sum(~(df[~idx][curr_var] >= 2)), np.sum(~(df[idx][curr_var] >= 2))] ])

                    # get the p-value
                    chi2, pvalue, dof, ex = scipy.stats.chi2_contingency( tbl )

                    # print out < 0.001 if it's a very low p-value
                    if pvalue < 0.001:
                        pvalue = '< 0.001'
                    else:
                        pvalue = '{:0.3f}'.format(pvalue)

                    print('{:20s}\t{:4g} ({:2.1f}%)\t{:4g} ({:2.1f}%)\t{:5s}'.format(curr_var.replace('_max',' ') + '> 2',
                    np.sum( df[~idx][curr_var] >= 2 ),
                    100.0*np.mean(df[~idx][curr_var] >= 2),
                    np.sum( df[idx][curr_var] >= 2 ),
                    100.0*np.mean(df[idx][curr_var] >= 2),
                    pvalue))

            else:
                print('{:20s}'.format(curr_var))


def calc_predictions(df, preds_header, target_header, model=None, print_summary=False):
    # default formula: evaluate the MFP model without severity of illness
    formula = target_header + " ~ age + elixhauser_hospital + is_male + race_black + race_other"
    if model is None:
        preds = dict()
        for x in preds_header:
            preds[x] = df[x].values
        return preds

    elif model == 'mfp_baseline':
        # call a subprocess to run the R script to generate fractional polynomial predictions
        formula = formula.replace(" age ", " fp(age) ").replace(" elixhauser_hospital "," fp(elixhauser_hospital) ")
        # loop through each severity score, build an MFP model for each
        fn_in = "sepsis3-design-matrix.csv"
        fn_out = "sepsis3-preds.csv"

        # by excluding the 4th argument, we train a baseline MFP model
        rcmd = ["Rscript r-make-sepsis3-models.R", fn_in, fn_out, '"' + formula + '"']
        err = subprocess.call(' '.join(rcmd), shell=True)
        if err!=0:
            print(' '.join(rcmd))
            print('RScript returned error status {}.'.format(err))
            return None
        else:
            # load in the predictions
            # base formula for the model
            pred = pd.read_csv(fn_out, sep=',', header=0)
            pred = pred.values[:,0]
        return pred

    elif model == 'logreg':
        P = len(preds_header)
        y = df[target_header].values == 1
        preds = dict()
        for p in range(P):
            # build the models adding each predictor as a covariate
            model = logit(formula=formula + " + " + preds_header[p],data=df).fit(disp=0)

            # create a list, each element containing the predictions
            preds[preds_header[p]] = model.predict()
            if print_summary == True:
                print(model.summary())
        return preds

    elif model == 'mfp':
        # call a subprocess to run the R script to generate fractional polynomial predictions
        formula = formula.replace(" age ", " fp(age) ").replace(" elixhauser_hospital "," fp(elixhauser_hospital) ")
        # loop through each severity score, build an MFP model for each
        fn_in = "sepsis3-design-matrix.csv"
        fn_out = "sepsis3-preds.csv"
        preds = dict()
        for p in preds_header:
             # note we add covariate 'p' to the formula
            rcmd = ["Rscript r-make-sepsis3-models.R", fn_in, fn_out, '"' + formula + " + fp(" + p + ')"']
            err = subprocess.call(' '.join(rcmd), shell=True)
            if err!=0:
                print(' '.join(rcmd))
                print('RScript returned error status {}.'.format(err))
            else:
                # load in the predictions
                pred = pd.read_csv(fn_out, sep=',', header=0)
                preds[p] = pred.values[:,0]
        return preds

    else:
        print('Unsure what {} means...'.format(model))
        return None


# measure of internal consistency for dicotomous data
# kuder richardson formula 20
def kr20(X):
    norm_factor = X.shape[1] / (X.shape[1]-1.0)

    kr20 = np.sum ( np.mean( X, axis=0 ) * np.mean( 1-X, axis=0 ) )
    kr20_var = np.mean( (np.sum(X, axis=1) - np.mean(np.sum(X,axis=1)))**2 )

    return norm_factor * (1-(kr20/kr20_var))

def kr20_bootstrap(X,B=1000):
    # bootstrap cronbach - return value and confidence intervals (percentile method)
    alpha = np.zeros(B,dtype=float)
    N = X.shape[1]

    for b in range(B):
        idx = np.random.randint(0, high=N, size=N)
        alpha[b] = cronbach_alpha(X[:,idx])

    ci = np.percentile(alpha, [5,95])
    alpha = cronbach_alpha(X)
    return alpha, ci

def cronbach_alpha(X):
    # given a set of with K components (K rows) of N observations (N columns)
    # we output the agreement among the components according to Cronbach's alpha
    X = np.asarray(X)
    return X.shape[0] / (X.shape[0] - 1.0) * (1.0 - (X.var(axis=1, ddof=1).sum() / X.sum(axis=0).var(ddof=1)))

def cronbach_alpha_bootstrap(X,B=1000):
    # bootstrap cronbach - return value and confidence intervals (percentile method)
    alpha = np.zeros(B,dtype=float)
    N = X.shape[1]

    for b in range(B):
        idx = np.random.randint(0, high=N, size=N)
        alpha[b] = cronbach_alpha(X[:,idx])

    ci = np.percentile(alpha, [5,95])
    alpha = cronbach_alpha(X)
    return alpha, ci

def corrcoef_bootstrap_tetrachoric(df, B=100):
    # write data to file and let R script bootstrap and get conf int
    alpha = np.zeros(B)
    fn_in = 'tetra-' + '-'.join(df.columns) + '.csv'
    df.to_csv(fn_in,index=False)
    rcmd = ["Rscript r-tetrachoric.R", fn_in, 'tetra-out.csv', str(B)]
    err = subprocess.call(' '.join(rcmd), shell=True)
    if err!=0:
        print(' '.join(rcmd))
        print('RScript returned error status {}.'.format(err))
    else:
        # load in the predictions
        corrcoef_df = pd.read_csv('tetra-out.csv', sep=',', header=0)
        alpha = corrcoef_df.values

    ci = np.percentile(alpha, [5,95])
    alpha = np.mean(alpha)
    return alpha, ci

def corrcoef_bootstrap(X,B=1000):
    # bootstrap correlation coefficient - return value and confidence intervals
    # (percentile method)
    alpha = np.zeros(B,dtype=float)
    N = X.shape[1]

    for b in range(B):
        idx = np.random.randint(0, high=N, size=N)
        # for 2 variables, corrcoef returns a 2x2 matrix
        corrcoef_mat = np.corrcoef(X[:,idx])
        # extract the correlation from the off-diagonal element
        alpha[b] = corrcoef_mat[0,1]

    ci = np.percentile(alpha, [5,95])
    alpha = np.corrcoef(X)[0,1]
    return alpha, ci

def print_auc_table(preds, target, preds_header, with_alpha=True):
    # prints a table of AUROCs and p-values like what was presented in the sepsis 3 paper
    y = target == 1
    P = len(preds)

    print('{:5s}'.format(''),end='\t')

    for p in range(P):
        print('{:20s}'.format(preds_header[p]),end='\t')

    print('')

    for p in range(P):
        ppred = preds_header[p]
        print('{:5s}'.format(ppred),end='\t')
        for q in range(P):
            qpred = preds_header[q]
            if ppred not in preds:
                print('{:20s}'.format(''),end='\t') # skip this as we do not have the prediction
            elif p==q:
                auc, ci = ru.calc_auc(preds[ppred], y, with_ci=True, alpha=0.05)
                print('{:0.3f} [{:0.3f}, {:0.3f}]'.format(auc, ci[0], ci[1]), end='\t')
            elif qpred not in preds:
                print('{:20s}'.format(''),end='\t') # skip this as we do not have the prediction
            elif q>p:
                if with_alpha == False:
                    # skip printing cronbach alpha as requested by input
                    print('{:20s}'.format(''),end='\t')
                else:
                    alpha, ci = cronbach_alpha_bootstrap(np.row_stack([preds[ppred],preds[qpred]]),B=2000)
                    print('{:0.3f} [{:0.3f}, {:0.3f}]'.format(alpha, ci[0], ci[1]), end='\t')
            else:
                pval, ci = ru.test_auroc(preds[ppred], preds[qpred], y)
                if pval > 0.001:
                    print('{:0.3f}{:15s}'.format(pval, ''), end='\t')
                else:
                    print('< 0.001{:15s}'.format(''),end='\t')


        print('')

def print_auc_table_to_file(preds, target, preds_header=None, filename=None):
    # prints a table of AUROCs and p-values
    # also train the baseline model using df_mdl
    # preds is a dictionary of predictions
    if filename is None:
        filename = 'auc_table.csv'

    f = open(filename,'w')


    if preds_header is None:
        preds_header = preds.keys()

    P = len(preds_header)
    y = target == 1
    f.write('{}\t'.format(''))

    # print header line
    for p in range(P):
        f.write('{}\t'.format(preds_header[p]))
    f.write('\n')

    for p in range(P):
        f.write('{}\t'.format(preds_header[p]))
        pname = preds_header[p]
        for q in range(P):
            qname = preds_header[q]
            if pname not in preds:
                f.write('{}\t'.format('')) # skip this as we do not have the prediction
            elif p==q:
                auc, ci = ru.calc_auc(preds[pname], y, with_ci=True, alpha=0.05)
                f.write('{:0.3f} [{:0.3f}, {:0.3f}]\t'.format(auc, ci[0], ci[1]))
            elif q>p:
                #TODO: cronenback alpha
                f.write('{}\t'.format(''))

            else:
                if qname not in preds:
                    f.write('{}\t'.format('')) # skip this as we do not have the prediction
                else:
                    pval, ci = ru.test_auroc(preds[pname], preds[qname], y)
                    if pval > 0.001:
                        f.write('{:0.3f}{}\t'.format(pval, ''))
                    else:
                        f.write('< 0.001{}\t'.format(''))


        f.write('\n')

    f.close()


def cronbach_alpha_table(df, preds_header, with_ci=True):
    # create a dataframe of Cronbach Alpha values
    # if CI requested, confidence intervals are also returned
    P = len(preds_header)

    df_out = pd.DataFrame(columns=preds_header)

    for p in range(P):
        ppred = preds_header[p]
        for q in range(P):
            if q==0:
                continue
            qpred = preds_header[q]
            if (ppred in df.columns) and (qpred in df.columns) and (p<q):
                if with_ci:
                    alpha, ci = cronbach_alpha_bootstrap(np.row_stack([df[ppred].values,df[qpred].values]),B=100)
                    df_out.loc[ppred, qpred] = '{:0.2f} [{:0.2f}-{:0.2f}]'.format(alpha, ci[0], ci[1])
                else:
                    alpha = cronbach_alpha(np.row_stack([df[ppred].values,df[qpred].values]))
                    df_out.loc[ppred, qpred] = alpha

    return df_out

def corrcoef_table(df, preds_header, with_ci=True, corr_type=None):
    # prints a table of AUROCs and p-values like what was presented in the sepsis 3 paper
    P = len(preds_header)
    print('{:8s}'.format(''),end='\t')

    for p in range(P):
        if p==0:
            continue
        print('{:8s}'.format(preds_header[p].replace('sepsis_','')),end='\t')
    print('')

    for p in range(P):
        ppred = preds_header[p]
        print('{:8s}'.format(ppred.replace('sepsis_','')),end='\t')
        for q in range(P):
            if q==0:
                continue
            qpred = preds_header[q]
            if (ppred in df.columns) and (qpred in df.columns) and (p<q):
                if corr_type == 'tetrachoric':
                    alpha, ci = corrcoef_bootstrap_tetrachoric(df[[ppred,qpred]],B=100)
                else:
                    alpha, ci = corrcoef_bootstrap(np.row_stack([df[ppred].values,df[qpred].values]),
                    B=100)
                print('{:0.2f} [{:0.2f}-{:0.2f}]'.format(alpha, ci[0], ci[1]), end=' ')
            else:
                # skip this for any other reason
                print('{:10s}'.format(''),end='\t')
        print('')

def kr20_table(df, preds_header, with_ci=True):
    # prints a table of AUROCs and p-values like what was presented in the sepsis 3 paper
    P = len(preds_header)

    print('{:10s}'.format(''),end='\t')

    for p in range(P):
        print('{:20s}'.format(preds_header[p]),end='\t')

    print('')

    for p in range(P):
        ppred = preds_header[p]
        print('{:10s}'.format(ppred),end='\t')
        for q in range(P):
            qpred = preds_header[q]
            if (ppred in df.columns) and (qpred in df.columns) and (p<q):
                alpha, ci = kr20_bootstrap(np.row_stack([df[ppred].values,df[qpred].values]),B=100)
                print('{:0.3f} [{:0.3f}, {:0.3f}]'.format(alpha, ci[0], ci[1]), end='\t')
            else:
                # skip this for any other reason
                print('{:20s}'.format(''),end='\t')


        print('')

def binomial_proportion(N, p, x1, x2):
    p = float(p)
    q = p/(1-p)
    k = 0.0
    v = 1.0
    s = 0.0
    tot = 0.0

    while(k<=N):
            tot += v
            if(k >= x1 and k <= x2):
                    s += v
            if(tot > 10**30):
                    s = s/10**30
                    tot = tot/10**30
                    v = v/10**30
            k += 1
            v = v*q*(N+1-k)/k
    return s/tot

# confidence intervals
def binomial_proportion_ci(numerator, denominator, alpha = 0.05):
    '''
    Calculate the confidence interval for a proportion of binomial counts.
    Confidence intervals calculated are symmetric.

    Sourced from @Kurtis from
    http://stackoverflow.com/questions/13059011/is-there-any-python-function-library-for-calculate-binomial-confidence-intervals
    ... which was based upon: http://statpages.info/confint.html
    ... which was further based upon:
        CJ Clopper and ES Pearson, "The use of confidence or fiducial limits
        illustrated in the case of the binomial." Biometrika. 26:404-413, 1934.

        F Garwood, "Fiducial Limits for the Poisson Distribution" Biometrica.
        28:437-442, 1936.
    '''
    numerator = float(numerator)
    denominator = float(denominator)
    p = alpha/2

    ratio = numerator/denominator
    if numerator==0:
            interval_low = 0.0
    else:
            v = ratio/2
            vsL = 0
            vsH = ratio

            while((vsH-vsL) > 10**-5):
                    if(binomial_proportion(denominator, v, numerator, denominator) > p):
                            vsH = v
                            v = (vsL+v)/2
                    else:
                            vsL = v
                            v = (v+vsH)/2
            interval_low = v

    if numerator==denominator:
            interval_high = 1.0
    else:
            v = (1+ratio)/2
            vsL = ratio
            vsH = 1
            while((vsH-vsL) > 10**-5):
                    if(binomial_proportion(denominator, v, 0, numerator) < p):
                            vsH = v
                            v = (vsL+v)/2
                    else:
                            vsL = v
                            v = (v+vsH)/2
            interval_high = v
    return (interval_low, interval_high)

def create_grouped_hist(df, groups, idxA, strAdd=None, targetStr='hospital_expire_flag'):
    x = np.zeros([2*len(groups),])

    # create an x-tick label during the loop
    lbl=list()
    i=0
    for lc in groups:
        # first group
        lbl.append(lc)
        idx = groups[lc] & ~idxA
        if len(strAdd)>1:
            lbl[i] += '\n' + strAdd[0]
        x[i] = np.mean(df.loc[idx, targetStr])
        i=i+1

        # second group
        lbl.append(lc)
        idx = groups[lc] & idxA
        if len(strAdd)>1:
            lbl[i] += '\n' + strAdd[1]
        x[i] = np.mean(df.loc[idx, targetStr])
        i=i+1

    return x, lbl

def create_venn_diagram(df, venn_labels, figsize=[10,9], percent_only=False):
    """
    df - dataframe with data
    venn_labels - ordered dictionary
       keys are the column names to be used in the venn diagram - columns should only have 0s/1s
       values are the "pretty" label for the column
    """
    sets = list()
    set_names = list()
    for c in venn_labels:
        idx = df[c]==1
        sets.append(set(df.loc[idx,'icustay_id']))
        set_names.append(venn_labels[c])


    if len(venn_labels)>4:
        print('Only supports up to a 4 set venn diagrams')
        return

    if len(venn_labels)==4:
        if percent_only:
            fill='percent_only'
        else:
            fill='percent'

        print('4d Venn diagrams not currently implemented.')
        #venn.venn4(sets, set_names,
        #           show_plot=False, fontdict={'fontsize': 15, 'fontweight': 'normal'},
        #           fill=fill, figsize=figsize)
        #leg = plt.legend('off')
        #leg.remove()
        #plt.show()
    else:
        if percent_only:
            string_formatter = lambda x: '{:2.1f}%'.format(x*100.0/df.shape[0])
        else:
            string_formatter = lambda x: '{:,}\n{:2.1f}%'.format(x, x*100.0/df.shape[0])

        plt.figure(figsize=figsize)
        plt.rcParams.update({'font.size': 15})
        venn3(sets, set_names, subset_label_formatter=string_formatter)
        plt.show()

    # excluded IDs
    set_other = set(df['icustay_id'].values).difference(*sets)

    # Print other numbers for above venn diagram
    print('{} patients ({:2.1f}%) satisfied all criteria.'.format(len(set.intersection(*sets)),
         len(set.intersection(*sets))*100.0 / df.shape[0]))
    print('{} patients ({:2.1f}%) satisfied no criteria.'.format(
            len(set_other),
            len(set_other)*100.0 / df.shape[0]))

    # pair-wise counts
    for i, c1 in enumerate(venn_labels):
        for j, c2 in enumerate(venn_labels):
            if i<=j:
                continue
            else:
                set_both = set.intersection(sets[i],sets[j])
                print('{:2.1f}% ({}) - {} & {}'.format(
                        len(set_both)*100.0 / df.shape[0], len(set_both),c1, c2))

    """
    for i, c1 in enumerate(venn_labels):
        for j, c2 in enumerate(venn_labels):
            set_both = set.difference(sets[i],sets[j])
            print('{:01.2f}%\t({:5d}) - overlap of {} and {} over {}'.format(
                    (len(sets[i]) - len(set_both))*100.0 / len(sets[i]), len(sets[i]) - len(set_both), c1, c2, c1))
    """
