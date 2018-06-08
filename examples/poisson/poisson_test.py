#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  23:48
Date created:  19/01/2018

License: MIT
'''
from pysppl.foppl import imports
import poisson as test
from pyfo.inference.dhmc import DHMCSampler as dhmc

dhmc_ = dhmc(test)

burn_in = 10 ** 2
n_sample = 10 ** 3

stepsize_range = [0.03,0.15]
n_step_range = [10, 20]

stats = dhmc_.sample(n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range, plot_graphmodel=True, print_stats=True,plot=True, save_samples=True)

samples =  stats['samples']
all_samples = stats['samples_wo_burin'] # type, panda dataframe


# samples = stats['samples']
# means = stats['means']
# print(means)
print(stats['accept_ratio'])