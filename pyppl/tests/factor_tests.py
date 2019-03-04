#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  13:55
Date created:  07/01/2019

License: MIT
'''

from pyppl import compile_model
from pyppl.utils.core import create_network_graph, display_graph

model_rrhmc_clojure="""
(let [x (sample (uniform -6 6))
       absx (max x (- x))
       A 0.1
       z (- (sqrt (* x (* A x))))]
 (if (< (- absx 3) 0)
     (observe (factor z) 0)
     (observe (factor (- z 1)) 0 ))
 x)
"""

model_rrhmc_python= """
import torch
x = sample(uniform(-6,6))
absx = max(x, -x)
A = 0.1
z = -torch.sqrt(x*A*x)
if absx-3 < 0:
    observe(factor(z),None)
    observe(factor(z-1),None)
"""
compiled_clojure = compile_model(model_rrhmc_clojure, language='clojure')
compiled_python = compile_model(model_rrhmc_python, language='python')

print(compiled_python.code)
