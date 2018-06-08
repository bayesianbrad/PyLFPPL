#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  21:34
Date created:  20/01/2018

License: MIT
'''
from pyppl.utils.core import create_network_graph, display_graph
from pyppl import compile_model
model_clojure = """(let[z (sample (categorical [0.7 0.15 0.15]))
            z1 (sample (categorical [0.1 0.5 0.4]))
            z2 (sample (categorical [0.2 0.2 0.6]))]
          z z1 z2)"""

model_if_clojure="""
(let [x1 (sample (normal 0 1))
      x2 (sample (categorical [0.1 0.2 0.7]))
      y1 7]
  (if (> x1 0)
    (if (> x2 1)
      (observe (normal x1 1) y1)
      (observe (normal (+ x1 x2) 2) y1))
    (observe (normal x2 1) y1) )
  [x1 x2])
"""


compiled_clojure = compile_model(model_if_clojure, language='clojure')
print(compiled_clojure.code)
vertices = compiled_clojure.vertices
create_network_graph(vertices=vertices)
display_graph(vertices=vertices)

model_python="""
import torch

n = 1
d = 1
x = sample(normal(torch.zeros(n,d), torch.ones(n,d)))
x
"""


model_neural_net ="""
import torch
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
# unclear from original model.
result.append( flip(1, probs=sigmoid(torch.mm(V.t(), h) + c)))

"""
compiled_python = compile_model(model_neural_net, language='python', imports='')

print(compiled_python.code)
print(compiled_python.display_graph)
print(dir(compiled_python))
vertices = compiled_python.vertices
create_network_graph(vertices=vertices)
display_graph(vertices=vertices)