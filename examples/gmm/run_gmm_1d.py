#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  11:29
Date created:  19/01/2018

License: MIT
'''
import tests.unittests.models.gmm.gmm_1d_c as test

# print(test.code)
from pyfo.inference.dhmc import DHMCSampler as dhmc

dhmc_ = dhmc(test)

burn_in = 100
n_sample = 100
stepsize_range = [0.03,0.15]
n_step_range = [1, 2]
# test.model.display_graph()
stats = dhmc_.sample(n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range,plot=False, print_stats=True, save_samples=True)
#
# samples =  stats['samples']
# all_samples = stats['samples_wo_burin'] # type, panda dataframe
# print(stats['accept_prob'])
