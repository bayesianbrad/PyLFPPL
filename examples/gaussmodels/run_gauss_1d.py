#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tests.unittests.models.gaussmodels.gauss_1d as test

from pyfo.inference.dhmc import DHMCSampler as dhmc
from pyfo.utils.eval_stats import *

# model
print(test.model)
test.model.display_graph()

# inference
n_chain = 3
dhmc_ = dhmc(test, chains=n_chain)
burn_in = 10
n_sample = 10
stepsize_range = [0.03,0.15]
n_step_range = [10, 20]

# all_stats = dhmc_.sample_multiple_chains(n_sample, burn_in=burn_in, stepsize_range=stepsize_range, n_step_range=n_step_range, n_update = 5,save_samples = True)

for i in all_stats:
    print('Chain {}: acceptance rate {} \n'.format(i, all_stats[i]['accept_rate'] ))

### MCMC diagnotics:
all_vars = list(all_stats[0]['samples'])
mu_true = np.array([5.28])
var_true = np.array([1.429**2])
for key in all_vars:
    _, n_dim =  all_stats[0]['samples'].as_matrix(columns=[key]).shape
    for i in range(n_chain):
        samples = np.empty(shape=(n_chain, n_sample, n_dim))
        samples[i] = all_stats[i]['samples'].as_matrix(columns=[key])
    ess = effective_sample_size(samples, mu_true, var_true)
    ess_mc = effective_sample_size(samples)
    r_hat = gelman_rubin_diagnostic(samples)
    print('ess for {}: '.format(key), ess)
    print('monte carlo ess for {}: '.format(key), ess_mc)
    print('r value for '.format(key), r_hat)


### MCMC diagnotics:
# samples =  stats['samples']
# all_samples = stats['samples_wo_burin'] # type, panda dataframe
#
# means = stats['means']
# print(means)
# x = samples.as_matrix(columns=['x'])
# t,d = x.shape
# x_ = np.empty(shape=(n_batch,t,d))
# x_[0] = x
# x_[1] = x
# mu_true = [5.28]
# var_true = [1.429**2]
#
# ess = effective_sample_size(x_, mu_true, var_true)
# print(ess)
#
# r_hat = gelman_rubin_diagnostic(x_)
# r_truemean = gelman_rubin_diagnostic(x_, mu_true)
# print('r value: ', r_hat, r_truemean)




