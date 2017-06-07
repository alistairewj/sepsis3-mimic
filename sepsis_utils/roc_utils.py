# tools for calculating/comparing the area under the receiver operator characteristic curve

import numpy as np
from scipy.stats import norm
import scipy as sp

# used to calculate exact AUROC (factoring in ties)
from sklearn import metrics

def calc_auc(pred, target, with_ci=False, alpha=0.05):
    # calculate the AUROC given one prediction or a set of predictions
    # returns a float if only one set of predictions given
    # returns a tuple if multiple predictions are given

    if type(pred) == 'list':
        pred = np.asarray(pred,dtype=float)
    if type(target) == 'list':
        target = np.asarray(target,dtype=float)

    if len(pred) == len(target):
        # we are calculating AUROC for a single prediction
        # encase it in a tuple for compatibility .. unwrap it later !
        pred = [pred]
        onePred = True
    else:
        if 'array' not in (pred[0]):
            print('Input sizes may not match!')
        if len(pred[0]) != len(target):
            print('Input sizes may not match!')
        onePred = False

    P = len(pred)
    N = len(target)

    W = list()
    for p in range(P):
        W.append(metrics.roc_auc_score(target, pred[p]))
    W = np.asarray(W,dtype=float)

    # collapse W down from array if only one prediction given
    if onePred == True:
        W = W[0]

    if with_ci == False:
        return W

    # calculate confidence interval and also return that
    S = calc_auc_cov(pred, target)

    if onePred == True:
        # collapse S into a single value
        # this allows auc_ci to be a (2,) sized array, rather than (1,2)
        S = S[0,0]

    auc_ci = norm.ppf([alpha/2.0, 1-(alpha/2.0)], loc=W, scale=np.sqrt(S))
    return W, auc_ci

def calc_auc_no_ties(pred, target):
    # calculate the AUROC given one prediction or a set of predictions
    # returns a float if only one set of predictions given
    # returns a tuple if multiple predictions are given

    if len(pred) == len(target):
        # we are calculating AUROC for a single prediction
        # encase it in a tuple for compatibility .. unwrap it later !
        pred = [pred]

    P = len(pred)
    N = len(target)

    W = list()
    for p in range(P):
        idx = np.argsort(pred[p])
        tar = target[idx]==0

        # calculate the number of negative cases below the current case
        pos = np.cumsum(tar)

        # index to only positive cases - i.e. number of negative cases below each positive case
        pos = pos[~tar]

        # sum the number of negative cases below each positive case
        W.append(np.sum(pos))

    W = np.asarray(W,dtype=float)
    N0 = np.sum(target==0)
    N1 = N-N0
    W = W / (N0*N1)

    if len(W)==1:
        W = W[0]

    return W

def calc_auc_cov(pred, target):

    P = len(pred) # number of predictors
    N = len(target) # number of observations


    # convert from tuple of predictions to matrix of X/Y
    idx = target==1

    # DeLong and DeLong define X as the group with *positive* target
    # Y as the group with *negative* target
    N_X = sum( idx) # number of positive cases
    N_Y = sum(~idx) # number of negative cases

    X = np.zeros([N_X, P])
    Y = np.zeros([N_Y, P])

    for p in range(P):
        X[:,p] = pred[p][ idx]
        Y[:,p] = pred[p][~idx]


    theta=np.zeros([P,1],dtype=float);
    V10=np.zeros([N_X,P],dtype=float);
    V01=np.zeros([N_Y,P],dtype=float);

    for p in range(P): # For each X/Y column pair
        # compare 0s to 1s
        for i in range(N_X):
            phi1=np.sum( X[i,p]  > Y[:,p] ); # Xi>Y
            phi2=np.sum( X[i,p] == Y[:,p] ); # Xi=Y
            V10[i,p]=(phi1+phi2*0.5);
            theta[p]=theta[p]+phi1+phi2*0.5;

        theta[p] = theta[p]/(N_X*N_Y);

        for j in range(N_Y):
            phi1=np.sum( X[:,p]  > Y[j,p] ); # X>Yj
            phi2=np.sum( X[:,p] == Y[j,p] ); # X=Yj
            V01[j,p] = (phi1+phi2*0.5);

    V10 = V10/N_Y
    V01 = V01/N_X

    #  Calculate S01 and S10, covariance matrices of V01 and V10
    theta_svd = np.dot(theta,np.transpose(theta))
    S01 = (1.0/(N_Y-1))*(np.dot(np.transpose(V01),V01) - N_Y*theta_svd);
    S10 = (1.0/(N_X-1))*(np.dot(np.transpose(V10),V10) - N_X*theta_svd);

    # Combine for S, covariance matrix of theta
    S = (1.0/N_Y)*S01 + (1.0/N_X)*S10;

    return S

def test_auroc(pred1, pred2, target, alpha=0.95):
    # compare if two predictions have AUROCs which are statistically significantly different
    S       = calc_auc_cov(pred=(pred1, pred2), target=target);
    theta   =     calc_auc(pred=(pred1, pred2), target=target)

    S_sz = S.shape;
    theta_sz = theta.shape;

    L = np.reshape(np.asarray([1, -1]),[1,2]) # the default contrast - compare pred1 to pred2
    LSL = np.dot(np.dot(L, S), np.transpose(L))

    # Compute p-value using normal distribution
    mu=np.dot(L,theta);
    sigma=np.sqrt(LSL);
    pval = sp.stats.distributions.norm.cdf(0,loc=mu,scale=sigma);
    pval = pval[0][0]
    # 2-sided test, double the tails -> double the p-value
    if mu<0:
        pval=2*(1-pval);
    else:
        pval=2*pval;

    # also output 95% confidence interval
    ci = sp.stats.distributions.norm.ppf([alpha/2,1-alpha/2],loc=theta[0],scale=sigma);

    return pval, ci

#TODO: also allow for comparing using contrast matrix / chi2 test

# bootstrap AUROC
def bootstrap_auc(pred, target, B=100):

    auc = np.zeros(B,dtype=float)
    N = len(target)

    for b in range(B):
        idx = np.random.randint(0, high=N, size=N)
        auc[b] = calc_auc(pred[idx], target[idx])

    # get confidence intervals using percentiles of AUC

    ci = np.percentile(auc, [5,95])
    auc = calc_auc(pred, target)

    return auc, ci

# === binormal AUROC is a parametric estimate of the ROC curve
# can be useful if you have low sample sizes

# assumes that the predictor is normally distributed, so sometimes it helps to
# transform the predictor to be more normally distributed, e.g. apply log, etc.

def binormal_auroc(X, Y):
    # calculates the AUROC assuming X and Y are normally distributed
    # this is frequently called the "Binormal AUROC"

    # X should contain predictions for observations with an outcome of 1
    # Y should contain predictions for observations with an outcome of 0

    x_mu = np.mean(X)
    x_s = np.std(X)

    y_mu = np.mean(Y)
    y_s = np.std(Y)

    a = (x_mu - y_mu) / x_s
    b = y_s / x_s

    return norm.cdf( a / (np.sqrt(1+(b**2))) )

def binormal_roc(X, Y, thr=None):
    # calculates the ROC curve assuming X and Y are normally distributed
    # uses evenly spaced points specified by thr
    # this is frequently called the "Binormal AUROC"

    # X should contain predictions for observations with an outcome of 1
    # Y should contain predictions for observations with an outcome of 0

    if thr is None:
        # get all possible criterion values
        c_vec = np.unique(np.concatenate([X, Y]))

        # create a vector of thresholds
        c_vec = np.linspace(np.min(c_vec), np.max(c_vec), 101)


    x_mu = np.mean(X)
    x_s = np.std(X)

    y_mu = np.mean(Y)
    y_s = np.std(Y)

    a = (x_mu - y_mu) / x_s
    b = y_s / x_s

    fpr = norm.cdf( (y_mu - c_vec) / y_s )
    tpr = norm.cdf( (x_mu - c_vec) / x_s )

    return fpr, tpr, c_vec
