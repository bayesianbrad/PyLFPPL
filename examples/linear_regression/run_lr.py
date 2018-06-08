#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  21:34®
Date created:  20/01/2018

License: MIT
'''
import tests.unittests.models.linear_regression.lr as test

print(test)

from pyfo.inference.dhmc import DHMCSampler as dhmc

dhmc_ = dhmc(test)
burn_in = 1000
n_sample = 2000
stepsize_range = [0.03,0.15]
n_step_range = [10, 20]

stats = dhmc_.sample(n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range,plot=True, print_stats=True, save_samples=True)