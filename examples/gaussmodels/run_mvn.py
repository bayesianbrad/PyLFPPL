#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pyfo.inference.dhmc import DHMCSampler as dhmc
from pyfo.utils.eval_stats import *
from tests.unittests.models import model

dhmc_ = dhmc(model)
burn_in = 10 ** 3
n_sample = 10 ** 3
stepsize_range = [0.03,0.15]
n_step_range = [10, 20]

stats = dhmc_.sample(n_samples=n_sample,burn_in=burn_in,stepsize_range=stepsize_range,n_step_range=n_step_range)

samples =  stats['samples']
all_samples = stats['samples_wo_burin'] # type, panda dataframe

print('mean_samples: ', extract_means(samples) , '\n')
print('mean_all_samples: ', extract_means(all_samples) , '\n')

# samples = stats['samples']
# means = stats['means']
# print(means)
# print(stats['accept_prob'])