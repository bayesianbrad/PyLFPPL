#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  15:08
Date created:  09/06/2018

License: MIT
'''
import torch
# def data(k):
#     points = torch.tensor([0.9, 0.8, 0.7, 0.0, -0.025,
#                        5.0, 2.0, 0.1, 0.0, 0.13,
#                        0.45, 6.0, 0.2, 0.3, -1.0, -1.0])
#     return points[k]

# Define the init, transition, and observation distributions
def get_init_params():
    return torch.tensor([1/3, 1/3, 1/3])

# def get_trans_params(k):
#     transition = torch.tensor([[0.1, 0.5, 0.4], [0.2, 0.2, 0.6], [0.7, 0.15, 0.15]])
#     return transition[:,k]

# def get_obs_dist(k):
#     observe = [normal(-1., 1.), normal(1.,1.), normal(0.,1.)]
#     return observe[k]

# Function to step through HMM and sample latent state

def hmm_step(k, states):
    transition = torch.tensor([[0.1, 0.5, 0.4], [0.2, 0.2, 0.6], [0.7, 0.15, 0.15]])

    next_state = sample(categorical(transition[:,states[-1]]))
    observe = [normal(-1., 1.), normal(1., 1.), normal(0., 1.)]
    points = torch.tensor([0.9, 0.8, 0.7, 0.0, -0.025,
                           5.0, 2.0, 0.1, 0.0, 0.13,
                           0.45, 6.0, 0.2, 0.3, -1.0, -1.0])
    observe(observe[next_state], points[k])
    return states.append(next_state)

# Loop through the data
init_state = sample(categorical(get_init_params()))
states = [init_state]
for i in range(16):
    states = hmm_step(i,states)
