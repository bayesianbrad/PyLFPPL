#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  15:23
Date created:  05/02/2018

License: MIT
'''
import tests.unittests.models.semantics_models.semantics as test
from pyfo.inference.dhmc import DHMCSampler as dhmc

dhmc_ = dhmc(test)

burn_in = 10 ** 3
n_sample = 10 ** 3

stepsize_range = [0.03,0.15]
n_step_range = [10, 20]

stats = dhmc_.sample(n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range, plot_graphmodel=True, print_stats=True,plot=False, save_samples=True)

# samples =  stats['samples']
# all_samples = stats['samples_wo_burin'] # type, panda dataframe
