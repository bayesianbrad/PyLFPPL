#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  11:15
Date created:  27/01/2018

License: MIT
'''
from pysppl.foppl import imports
import dirichlet as test


from pyfo.inference.dhmc import DHMCSampler as dhmc

dhmc_ = dhmc(test)
burn_in = 300
n_sample = 300
stepsize_range = [0.03,0.15]
n_step_range = [10, 20]

stats = dhmc_.sample(n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range,plot=False, print_stats=True, save_samples=True)

print(stats['samples'])
print(stats['accept_ratio'])
