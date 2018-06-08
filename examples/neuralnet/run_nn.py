#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  20:08
Date created:  25/01/2018

License: MIT
'''
import tests.unittests.models.neuralnet.nn_Frank as test

from pyfo.inference.dhmc import DHMCSampler as dhmc

dhmc_ = dhmc(test)
burn_in =100
n_sample = 100
stepsize_range = [0.03,0.15]
n_step_range = [10, 20]
test.model.display_graph()
stats = dhmc_.sample(n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range, print_stats=True, save_samples=True)

samples =  stats['samples']
all_samples = stats['samples_wo_burin'] # type, panda dataframe
print(stats['accept_prob'])

