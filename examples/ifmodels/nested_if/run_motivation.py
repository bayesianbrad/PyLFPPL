#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  22:55
Date created:  07/02/2018

License: MIT
'''
import tests.unittests.models.ifmodels.nested_if.motivation as test

from pyfo.inference.dhmc import DHMCSampler as dhmc

# model
# print(test.model)
# test.model.display_graph()

# inference
dhmc_ = dhmc(test)
burn_in = 1000
n_sample = 1000
stepsize_range = [0.03,0.15]
n_step_range = [4, 15]
n_chain = 5

stats = dhmc_.sample(n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range,
                   plot=True, print_stats=True, save_samples=True, plot_ac=True)
# #
