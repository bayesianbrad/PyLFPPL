#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  10:49
Date created:  27/01/2018

License: MIT
'''
import tests.unittests.models.ifmodels.nested_if.nested_if as test

from pyfo.inference.dhmc import DHMCSampler as dhmc

# model
# print(test.model)
# test.model.display_graph()

# inference
n_chain = 5
dhmc_ = dhmc(test, chains=n_chain)
burn_in = 1000
n_sample = 1000
stepsize_range = [0.03, 0.15]
n_step_range = [4, 15]

stats = dhmc_.sample(n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range)
                     # plot=True, print_stats=True, save_samples=True, plot_ac=True)
#
# all_stats = dhmc_.sample_multiple_chains(n_chains=n_chain, n_samples=n_sample, burn_in=burn_in,
