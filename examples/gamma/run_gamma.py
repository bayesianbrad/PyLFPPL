#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  15:58
Date created:  26/01/2018

License: MIT
'''

from pysppl.foppl import imports
import gamma as test
from pyfo.inference.dhmc import DHMCSampler as dhmc

burn_in = 5
n_samples = 5
stepsize_range = [0.05, 0.25]
n_step_range = [10, 20]
# test.model.display_graph()
dhmc_ = dhmc(test)
stats = dhmc_.sample(n_samples, burn_in, stepsize_range, n_step_range, seed=123, print_stats=True)
