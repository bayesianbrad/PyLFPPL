#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  14:26
Date created:  13/03/2018

License: MIT
'''

from pyfoppl.foppl import *  # ignored by the compiler, but keeps the IDE happy
import torch

x1  = sample(normal(torch.tensor([0,2]), torch.tensor([1,4])))

x2 = sample(normal(torch.tensor([0,5]), torch.tensor([2,4])))

observations = torch.ones(len(x2))
# this could get potentially tricky. As although we are performing an ''if'' statement over a vector, we have no
# explict 'if-then-else' statements.
# it may be wise to have, in addition to oberve and sample statements and if statement in which the user writes,
#  if x1 > 0:
#       do something
# else:
#       do something
# and unpack this within the model as follows

boolean = torch.gt(x1, 0)
truth_index = boolean.nonzero() # indices for which the statement is true
false_index = (boolean==0).nonzero() # indices for which the statements are false.

# These may be able to vectorized further
for index in truth_index:
    observe(normal(x2[index], 1*torch.tensor(len(x2[index]))),observations[index])
for index in false_index:
    observe(normal(-1*torch.tensor(len(x2[index])), torch.tensor(len(x2[index]))), observations[index])

# Of course if groups of indices have different bounds, this would get
# potentially very tricky. However,  we can ignore the 2nd case for now.

# orignal code

# x1 = sample(normal(0, 2))
# x2 = sample(normal(0, 4))
# if x1 > 0
#     observe(normal(x2, 1), 1)
# else:
#     observe(normal(-1, 1), 1)