import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import pyplot
from statsmodels.distributions.empirical_distribution import ECDF

#--- [1] read data and only keep features and observations we want

#- [1.1] utility functions

def string_to_numbers(string):

    string = string.replace("[", "")
    string = string.replace("]", "")
    string = string.replace(" ", "")
    arr = string.split(',')
    arr = [eval(i) for i in arr]
    return(arr)

def category_to_integer(category):
    if category == 'Yes':
        integer = 1
    elif category == 'No':
        integer = 0
    else:
        integer = 2
    return(integer)

#- [1.2] read data

url = "https://raw.githubusercontent.com/VincentGranville/Main/main/iot_C2_full_nogan.csv"
# data = pd.read_csv('iot_C2_full_nogan.csv')
data = pd.read_csv(url)

# all features used here
features = ['bidirectional_syn_packets',	
            'src2dst_syn_packets',	
            'application_category_name',	
            'application_confidence',
            'src2dst_mean_ps',
            'src2dst_psh_packets',
            'bidirectional_mean_ps',	
            'label']

# declare categorical features
categorical = ['bidirectional_syn_packets',	
               'src2dst_syn_packets',	
               'application_category_name',	
               'application_confidence',
               'src2dst_psh_packets',
               'label']

print(data.head()) 
print (data.shape)
print (data.columns)

#- [1.3] data transforms TotalCharges to TotalChargeResidues, add to dataframe

# no transform used for the iot dataset

#- [1.4] set seed for replicability

pd.core.common.random_state(None)
seed = 105 
np.random.seed(seed)

#- [1.5] initialize hyperparameters (bins_per_feature), select features

bins_per_feature = [80, 80, 80, 80, 80, 80, 80, 80]   

bins_per_feature = np.array(bins_per_feature).astype(int)
data = data[features]
print(data.head())
print (data.shape)
print (data.columns)

#- [1.6] split real dataset into training and validation sets

data_training = data.sample(frac = 0.50)
data_validation = data.drop(data_training.index)
data_training.to_csv('iot_training_vg2.csv')
data_validation.to_csv('iot_validation_vg2.csv')

nobs = len(data_training)
n_features = len(features)
eps = 0.0000000001 


#--- [2] create synthetic data  

#- [2.1] create quantile table pc_table2, one row for each feature

pc_table2 = []
for k in range(n_features):
    label = features[k]
    incr = 1 / bins_per_feature[k]   
    pc = np.arange(0, 1 + eps, incr)
    arr = np.quantile(data_training[label], pc, axis=0)
    pc_table2.append(arr)

#- [2.2] create/update bin for each obs [layer 1]
#        Faster implementation: replace 'while' loop by dichotomic search

npdata = pd.DataFrame.to_numpy(data_training[features])
bin_count = {}   # number of obs per bin
bin_obs = {}     # list of obs in each bin, separated by "~", stored as a string
for obs in npdata:
    key = [] 
    for k in range(n_features):
        idx = 0
        arr = pc_table2[k]    # percentiles for feature k
        while obs[k] >= arr[idx] and idx < bins_per_feature[k]: 
            idx = idx + 1
        idx = idx - 1  # lower bound for feature k in bin[key] attached to obs
        key.append(idx)
        skey = str(key)
    if skey in bin_count:
        bin_count[skey] += 1
        bin_obs[skey] += "~" + str(obs)
    else:
        bin_count[skey] = 1
        bin_obs[skey] = str(obs)

#- [2.3] generate nobs_synth observations (if mode = FixedCounts, nobs_synth = nobs)

def random_bin_counts(n, bin_count):
    # generate multinomial bin counts with same expectation as real counts
    pvals = []
    for skey in bin_count:
        pvals.append(bin_count[skey]/nobs)
    return(np.random.multinomial(n, pvals))

def get_obs_in_bin(bin_obs, skey): 
    # get list of observations (real data) in bin skey, also return median
    arr_obs = []
    arr_obs_aux = (bin_obs[skey]).split('~')
    for obs in arr_obs_aux:
        obs = ' '.join(obs.split())
        obs = obs.replace("[ ", "")
        obs = obs.replace("[", "")
        obs = obs.replace(" ]", "")
        obs = obs.replace("]", "")
        obs = obs.split(' ')
        obs = (np.array(obs)).astype(float)
        arr_obs.append(obs)
    arr_obs = np.array(arr_obs)
    median = np.median(arr_obs, axis = 0)
    return(arr_obs, median) 

    
mode = 'RandomCounts'  # (options: 'FixedCounts' or 'RandomCounts')
if mode == 'RandomCounts':
    nobs_synth = 2*nobs 
    bin_count_random = random_bin_counts(nobs_synth, bin_count)
    ikey = 0

data_synth = []
bin_counter = 0

for skey in bin_count:

    if mode == 'FixedCounts':
        count = bin_count[skey]
    elif mode == 'RandomCounts': 
        count = bin_count_random[ikey]
        ikey += 1
    key = string_to_numbers(skey)
    L_bounds = []
    U_bounds = []
    bin_counter += 1

    for k in range(n_features):
        arr = pc_table2[k] 
        L_bounds.append(arr[key[k]])
        U_bounds.append(arr[1 + key[k]])

    # sample new synth obs (new_obs) in rectangular bin skey, uniformily
    # try other distrib, like multivariate Gaussian around bin median 
    # the list of real observations in bin[skey] is stored in obs_list (numpy array)
    # median is the vector of medians for all obs in bin skey

    obs_list, median = get_obs_in_bin(bin_obs, skey) # not used in this version
    
    for i in range(count):        
        new_obs = np.empty(n_features) # synthesized obs
        for k in range(n_features):
            new_obs[k] = np.random.uniform(L_bounds[k],U_bounds[k])
        data_synth.append(new_obs)

    str_median = str(["%8.2f" % number for number in median])
    str_median = str_median.replace("'","")
    print("bin ID = %5d | count = %5d | median = %s | bin key = %s" 
              %(bin_counter, bin_count[skey], str_median, skey))

data_synth = pd.DataFrame(data_synth, columns = features)

# apply floor function (not round) to categorical/ordinal features
data_synth[categorical] = data_synth[categorical].astype('int')


print(data_synth)    
data_synth.to_csv('iot_synth_vg2.csv')


#--- [3] Evaluation synthetization using joint ECDF & Kolmogorov-Smirnov distance

# dataframes: df = synthetic; data = real data,
# compute multivariate ecdf on validation set, sort it by value (from 0 to 1) 

#- [3.1] compute ecdf on validation set (to later compare with that on synth data)

def compute_ecdf(dataframe, n_nodes, adjusted):

    # Monte-Carlo: sampling n_nodes locations (combos) for ecdf
    #    - adjusted correct for sparsity in high ecdf, but is sparse in low ecdf  
    #    - non-adjusted is the other way around
    # for faster computation: pre-compute percentiles for each feature
    # foe faster computation: optimize the computation of n_nodes SQL-like queries

    ecdf = {} 

    for point in range(n_nodes):

        if point % 100 == 0:
            print("sampling ecdf, location = %4d (adjusted = %s):" % (point, adjusted))
        combo = np.random.uniform(0, 1, n_features)
        if adjusted:
            combo = combo**(1/n_features)
        z = []   # multivariate quantile
        query_string = ""
        for k in range(n_features):
            label = features[k]
            dr = data_validation[label]
            percentile = combo[k] 
            z.append(eps + np.quantile(dr, percentile))
            if k == 0:
                query_string += "{} <= {}".format(label, z[k])
            else: 
                query_string += " and {} <= {}".format(label, z[k])

        countifs = len(data_validation.query(query_string))
        if countifs > 0: 
            ecdf[str(z)] = countifs / len(data_validation)
  
    ecdf = dict(sorted(ecdf.items(), key=lambda item: item[1]))

    # extract table with locations (ecdf argument) and ecdf values:
    #     - cosmetic change to return output easier to handle than ecdf 

    idx = 0
    arr_location = []
    arr_value = []
    for location in ecdf:
        value = ecdf[location]
        location = string_to_numbers(location)
        arr_location.append(location)
        arr_value.append(value)
        idx += 1

    print("\n")
    return(arr_location, arr_value)


n_nodes = 1000   # number of random locations in feature space, where ecdf is computed
reseed = False
if reseed:
   seed = 555
   np.random.seed(seed) 
arr_location1, arr_value1 = compute_ecdf(data_validation, n_nodes, adjusted = True)
arr_location2, arr_value2 = compute_ecdf(data_validation, n_nodes, adjusted = False)

#- [3.2] comparison: synthetic (based on training set) vs real (validation set)

def ks_delta(SyntheticData, locations, ecdf_ValidationSet):

    # SyntheticData is a dataframe
    # locations are the points in the feature space where ecdf is computed
    # for the validation set, ecdf values are stored in ecdf_ValidationSet
    # here we compute ecdf for the synthetic data, at the specified locations
    # output ks_max in [0, 1] with 0 = best, 1 = worst

    ks_max = 0
    ecdf_real = []
    ecdf_synth = []
    for idx in range(len(locations)):
        location = locations[idx]
        value = ecdf_ValidationSet[idx]
        query_string = ""
        for k in range(n_features):
            label = features[k]
            if k == 0:
                query_string += "{} <= {}".format(label, location[k])
            else: 
                query_string += " and {} <= {}".format(label, location[k])
        countifs = len(SyntheticData.query(query_string))
        synth_value = countifs / len(SyntheticData)
        ks = abs(value - synth_value)
        ecdf_real.append(value)
        ecdf_synth.append(synth_value)
        if ks > ks_max:
            ks_max = ks
        # print("location ID: %6d | ecdf_real: %6.4f | ecdf_synth: %6.4f"
        #             %(idx, value, synth_value))
    return(ks_max, ecdf_real, ecdf_synth)

df = pd.read_csv('iot_synth_vg2.csv')
ks_max1, ecdf_real1, ecdf_synth1 = ks_delta(df, arr_location1, arr_value1)
ks_max2, ecdf_real2, ecdf_synth2 = ks_delta(df, arr_location2, arr_value2)
ks_max = max(ks_max1, ks_max2)
print("Test ECDF Kolmogorof-Smirnov dist. (synth. vs valid.): %6.4f" %(ks_max))

#- [3.3] comparison: training versus validation set

df = pd.read_csv('iot_training_vg2.csv')
base_ks_max1, ecdf_real1, ecdf_synth1 = ks_delta(df, arr_location1, arr_value1)
base_ks_max2, ecdf_real2, ecdf_synth2 = ks_delta(df, arr_location2, arr_value2)
base_ks_max = max(base_ks_max1, base_ks_max2)
print("Base ECDF Kolmogorof-Smirnov dist. (train. vs valid.): %6.4f" %(base_ks_max))

