#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  14:27
Date created:  13/03/2018

License: MIT
'''

import torch
from pyfoppl.foppl import *  # ignored by the compiler, but keeps the IDE happy
n = 2
x = sample(normal(3*torch.ones(n), 5*torch.ones(n)))
y = x + 1
observations = 7*torch.ones(n)
observe(normal(y, 2*torch.ones(n)), observations)
y
