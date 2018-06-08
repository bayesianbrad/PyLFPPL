#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  14:26
Date created:  13/03/2018

License: MIT
'''
from pyfoppl.foppl import *
import torch

# def sample_components(pi):
#     return sample(categorical(pi))
#
# def observe_data(y, z, mus):
#     mu = mus[z]
#     observe(normal(mu, 2), y)
#
# ys = [-2.0, -2.5, -1.7, -1.9, -2.2, 1.5, 2.2, 3.0, 1.2, 2.8]
# pi = [0.5, 0.5]
# zs = map(sample_components, pi * 10)
# mus = [sample(normal(0, 2)), sample(normal(0, 2))]
# for y, z in interleave(ys, zs):
#     observe_data(y, z, mus)

means  = 2
samples  = 10
ys = torch.tensor([-2.0, -2.5, -1.7, -1.9, -2.2, 1.5, 2.2, 3.0, 1.2, 2.8])
pi = torch.tensor([0.5, 0.5])
mus = sample(normal(torch.zeros(means), 2*torch.ones(means)))

zn = sample(categorical(pi, [10,]))
# Note: When you call .sample for categorical you can specify a torch.Size([n_rows, n_cols]) in the sample, to
# return the number of samples that you need. I.e x1 =   torch.distributions.Categorical(probs=pi)
#                                                   x1.sample(sample_shape=torch.Size([samples,])
for i in range(len(pi)):
    index = (zn == i).nonzero()
    observe(normal(mus[i]*torch.ones(len(index)), 2*torch.ones(len(index))), ys[index])