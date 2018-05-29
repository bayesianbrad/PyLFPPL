#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 21. Jan 2018, Tobias Kohn
# 01. Feb 2018, Tobias Kohn
#
import math as _math
import random as _random
####################################################################################################

class dist(object):
    """
    This class is a namespace with "stand-in" distributions for testing purposes. They are explicitly not
    meant to be used for actual sampling and evaluation. However, using these test-distributions allows us
    to test the frontend/compiler without the sophisticated backend doing actual inference.
    """

    class Dummy(object):

        def __init__(self, *args, **kwargs):
            pass

        def log_pdf(self, value):
            return 0

        log_prob = log_pdf

        def sample(self):
            return 1

    Binomial = Dummy
    Categorical = Dummy
    Dirichlet = Dummy
    Exponential = Dummy
    Gamma = Dummy
    LogGamma = Dummy
    MultivariateNormal = Dummy
    Poisson = Dummy
    Uniform = Dummy

    class Normal(object):

        def __init__(self, *args, **kwargs):
            self.mu = 0.0
            self.sigma = 1.0

        def log_pdf(self, value):
            return -1/2 * (((value - self.mu)**2 / self.sigma) + _math.log(2 * _math.pi * self.sigma))

        log_prob = log_pdf

        def sample(self):
            return _random.gauss(self.mu, self.sigma)


