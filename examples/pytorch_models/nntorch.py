#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  14:17
Date created:  13/03/2018

License: MIT
'''

from pyfoppl.foppl import *
import torch

#
# latent_dim = 2
# hidden_dim = 10
# output_dim = 5
#
# def gaussian():
#     return sample(normal(0.0, 1.0))
#
# def make_latent_vector():
#     return [gaussian() for _ in range(latent_dim)]
#
# def make_hidden_vector():
#     return [gaussian() for _ in range(hidden_dim)]
#
# def make_output_vector():
#     return [gaussian() for _ in range(output_dim)]
#
# def relu(v):
#     return matrix.mul(matrix.ge(v, 0.0), v)
#
# def sigmoid(v):
#     return matrix.div(1.0, matrix.add(1.0, matrix.exp(matrix.sub(0.0, v))))
#
# def flip(i, p):
#     return sample(binomial(p[i]))
#
# z = make_latent_vector()
# W = [make_latent_vector() for _ in range(hidden_dim)]
# b = make_hidden_vector()
# h = relu(matrix.add(matrix.mmul(W, z), b))
#
# V = [make_hidden_vector() for _ in range(output_dim)]
# c = make_output_vector()
#
# result = []
# for i in range(output_dim):
#     result.append( flip(i, sigmoid(matrix.add(matrix.mmul(V, h), c))) )


latent_dim = 2
hidden_dim = 10
output_dim = 5

def gaussian(n_samples):
    return sample(normal(0.0*torch.ones(n_samples), 1.0*torch.ones(n_samples)))

def make_latent_vector():
    return gaussian(latent_dim)

def make_hidden_vector():
    return gaussian(hidden_dim)

def make_output_vector():
    return gaussian(output_dim)

def relu(v):
    relu = torch.nn.ReLU()
    return relu(v)

def sigmoid(v):
    return torch.sigmoid(v)

def flip(i, probs):
    return sample(binomial(total_count=i,probs=probs))

z = make_latent_vector()
W = torch.stack([make_latent_vector() for _ in range(hidden_dim)], dim=1) # Creates a tenssor of dims latent_dim x hidden_dim (2 x10)
b = make_hidden_vector() #(10)
h = relu(torch.mm(W.t(), z.unsqueeze(-1))+ b) # (10 x 2 * 2 x 1 + 10) --> 10 x 1

V = torch.stack([make_hidden_vector() for _ in range(output_dim)], dim=1) # 10 x 5
c = make_output_vector() # 5

result = []
result.append( flip(total_coint=i, probs=sigmoid(torch.mm(V.t(), h) + c))) # 5 x 10 * 10 x 1 + 5