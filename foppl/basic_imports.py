#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Jan 2018, Tobias Kohn
# 01. Feb 2018, Tobias Kohn
#
"""
Change this file to provide all the necessary imports and namespaces for the functions and distributions used in the
model.
"""
import torch
from torch.autograd import Variable
import pyfo.distributions as dist
# from .test_distributions import dist
from . import foppl_linalg as matrix