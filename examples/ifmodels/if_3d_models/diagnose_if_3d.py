#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pysppl.foppl import imports
import pandas as pd
from pyfo.utils.eval_stats import *

PATH  = sys.path[0]
n_chain = 5
var_key = ['x1', 'x2', 'x3']

### load data
all_stats = load_data(n_chain,var_key,PATH)

### MCMC diagnotics:
all_vars = list(all_stats[0]['samples'])
for key in all_vars:
    n_sample, n_dim =  all_stats[0]['samples'].as_matrix(columns=[key]).shape
    for i in range(n_chain):
        samples = np.empty(shape=(n_chain, n_sample, n_dim))
        samples[i] = all_stats[i]['samples'].as_matrix(columns=[key])
    # ess = effective_sample_size(samples, mu_true, var_true)
    ess_mc = effective_sample_size(samples)
    r_hat = gelman_rubin_diagnostic(samples)
    # print('ess for {}: '.format(key), ess)
    print('monte carlo ess for {}: '.format(key), ess_mc)
    print('r value for '.format(key), r_hat)


