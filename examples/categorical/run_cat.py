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

model_hmm_clojure="""
(defn data [n]
  (let [points (vector 0.9 0.8 0.7 0.0 -0.025
                       5.0 2.0 0.1 0.0 0.13
                       0.45 6.0 0.2 0.3 -1.0 -1.0)]
    (get points n)))

;; Define the init, transition, and observation distributions
(defn get-init-params []
  (vector (/ 1. 3.) (/ 1. 3.) (/ 1. 3.)))

(defn get-trans-params [k]
  (nth (vector (vector 0.1  0.5  0.4 )
               (vector 0.2  0.2  0.6 )
               (vector 0.7 0.15 0.15 )) k))

(defn get-obs-dist [k]
  (nth (vector (normal -1. 1.)
               (normal  1. 1.)
               (normal  0. 1.)) k))

;; Function to step through HMM and sample latent state
(defn hmm-step [n states]
  (let [next-state (sample (categorical (get-trans-params (last states))))]
    (observe (get-obs-dist next-state) (data n))
    (conj states next-state)))

;; Loop through the data
(let [init-state (sample (categorical (get-init-params)))]
  (loop 16 (vector init-state) hmm-step))

"""
compiled_clojure = compile_model(model_if_clojure, language='clojure')
print(compiled_clojure.code)
vertices = compiled_clojure.vertices
create_network_graph(vertices=vertices)
display_graph(vertices=vertices)

model_if_python="""
x1 = sample(normal(0, 1))
x2 = sample(categorical([0.1, 0.2, 0.7]))
y1 =  7
if x1 > 0:
    if x2 > 1:
        observe(normal(x1,1),y1)
        observe(normal(x1 + x2, 2), y1)
    else:
        observe(normal(x2,1),y1)
[x1, x2]
"""
model_python="""
import torch

n = 1
d = 1
x = sample(normal(torch.zeros(n,d), torch.ones(n,d)))
x
"""

model_hmm_python="""
import torch
# def data(k):
#     points = torch.tensor([0.9, 0.8, 0.7, 0.0, -0.025,
#                        5.0, 2.0, 0.1, 0.0, 0.13,
#                        0.45, 6.0, 0.2, 0.3, -1.0, -1.0])
#     return points[k]

# Define the init, transition, and observation distributions
# def get_init_params():
#     return torch.tensor([1/3, 1/3, 1/3])

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
init_state = sample(categorical(probs=torch.tensor([1/3, 1/3, 1/3])))
states = [init_state]
for i in range(16):
    states = hmm_step(i,states)
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

# """
#
compiled_python = compile_model(model_if_python, language='python', imports='')

print(compiled_python.code)
# print(dir(compiled_python))
vertices = compiled_python.vertices
create_network_graph(vertices=vertices)
display_graph(vertices=vertices)