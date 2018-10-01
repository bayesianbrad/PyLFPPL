#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 17. Jan 2018, Tobias Kohn
# 28. Mar 2018, Tobias Kohn
#
from enum import *

#########################################################################

class DistributionType(Enum):

    CONTINUOUS = "continuous"
    DISCRETE   = "discrete"


#########################################################################

class Distribution(object):

    def __init__(self, name:str, distributions_type:DistributionType=None, params:list=None, *,
                 vector_sample:bool=False,
                 foppl_name:str=None,
                 python_name:str=None):
        assert type(name) is str
        self.name = name
        self.foppl_name = name.lower() if foppl_name is None else foppl_name
        self.python_name = name if python_name is None else python_name
        if distributions_type is None:
            self.distribution_type = DistributionType.CONTINUOUS
        else:
            self.distribution_type = distributions_type
        if params is None:
            self.params = []
        else:
            self.params = params
        self._vector_sample = vector_sample

    @property
    def is_continuous(self):
        return self.distribution_type == DistributionType.CONTINUOUS

    @property
    def is_discrete(self):
        return self.distribution_type == DistributionType.DISCRETE

    @property
    def parameter_count(self):
        return len(self.params)



#########################################################################

distributions = {
    Distribution('Bernoulli',   DistributionType.DISCRETE,   ['probs']),
    Distribution('Beta',        DistributionType.CONTINUOUS, ['alpha', 'beta']),
    Distribution('Binomial',    DistributionType.DISCRETE, ['total_count', 'probs']),
    Distribution('Categorical', DistributionType.DISCRETE,   ['probs']),
    Distribution('Cauchy',      DistributionType.CONTINUOUS, ['mu', 'gamma']),
    Distribution('Dirichlet',   DistributionType.CONTINUOUS, ['alpha'], vector_sample=True),
    Distribution('Discrete',    DistributionType.DISCRETE,   None),
    Distribution('Exponential', DistributionType.CONTINUOUS, ['rate']),
    Distribution('Gamma',       DistributionType.CONTINUOUS, ['alpha', 'beta']),
    Distribution('HalfCauchy',  DistributionType.CONTINUOUS, ['mu', 'gamma'], foppl_name='half_cauchy'),
    Distribution('LogGamma',    DistributionType.CONTINUOUS, ['alpha', 'beta']),
    Distribution('LogNormal',   DistributionType.CONTINUOUS, ['mu', 'sigma'], foppl_name='log_normal'),
    Distribution('Multinomial', DistributionType.DISCRETE,   ['total_count', 'probs', 'n']),
    Distribution('MultivariateNormal',
                                DistributionType.CONTINUOUS, ['mean', 'covariance_matrix'], vector_sample=True, foppl_name='mvn'),
    Distribution('Normal',      DistributionType.CONTINUOUS, ['loc', 'scale']),
    Distribution('Poisson',     DistributionType.DISCRETE,   ['rate']),
    Distribution('Uniform',     DistributionType.CONTINUOUS, ['low', 'high']),
    Distribution('Exp', DistributionType.CONTINUOUS, ['values'], foppl_name='Exp'),
    Distribution('Log', DistributionType.CONTINUOUS, ['values'], foppl_name='Log'),
    Distribution('Sin', DistributionType.CONTINUOUS, ['theta'], foppl_name='Sin'),
    Distribution('Cos', DistributionType.CONTINUOUS, ['theta'], foppl_name='Cos'),
    Distribution('Poly', DistributionType.CONTINUOUS, ['coeff', 'order'], foppl_name='Poly')

}

namespace = {
    d.foppl_name: 'dist.' + d.python_name for d in distributions
}

def get_distribution_for_name(name: str) -> Distribution:
    if name.startswith("dist."):
        return get_distribution_for_name(name[5:])
    for dist in distributions:
        if dist.name == name or dist.python_name == name or dist.foppl_name == name:
            return dist
    return None
