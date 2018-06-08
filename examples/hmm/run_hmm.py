#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  11:07
Date created:  20/01/2018

License: MIT
'''
import tests.unittests.models.hmm.hmm as test

from pyfo.inference.dhmc import DHMCSampler as dhmc

### model
# test.model.display_graph()
stepsize_range = [0.01,0.085]
n_step_range = [10, 40]
### inference
dhmc_ = dhmc(test)
burn_in = 8000
n_sample = 50000
# stepsize_range = [0.03,0.15]
# n_step_range = [10, 20]
# stepsize_range = [0.01,0.05]  # old parameters
# n_step_range = [5, 10]
n_chain = 3

all_stats = dhmc_.sample(chain_num = n_chain, n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range, save_samples=True)