#
# Generated: 2018-01-14 20:04:21.592232
#
import math
import numpy as np
import torch
from torch.autograd import Variable
import pyfo.distributions as dist
from pyfo.utils.interface import interface


class model(interface):
    """
	Vertices V:
	  x20001, y20002
	Arcs A:
	  (x20001, y20002)
	Conditional densities C:
	  x20001 -> dist.MultivariateNormal(mu=[0, 0], covariance_matrix=[[1, 0], [0, 1]])
	  y20002 -> dist.MultivariateNormal(mu=x20001, covariance_matrix=[[2, 0], [0, 2]])
	Observed values O:
	  y20002 -> [7, 7]
	"""
    vertices = {'y20002', 'x20001'}
    arcs = {('x20001', 'y20002')}
    names = {'x20001': 'x'}
    cond_functions = {

    }

    @classmethod
    def get_vertices(self):
        return list(self.vertices)

    @classmethod
    def get_arcs(self):
        return list(self.arcs)

    @classmethod
    def gen_cond_vars(self):
        return []

    @classmethod
    def gen_cont_vars(self):
        return ['x20001']

    @classmethod
    def gen_disc_vars(self):
        return []

    @classmethod
    def gen_if_vars(self):
        return []

    @classmethod
    def gen_pdf(self, state):
        dist_x20001 = dist.MultivariateNormal(mu=[0, 0], covariance_matrix=[[1, 0], [0, 1]])
		# dist_x20001 = dist.MultivariateNormal(mu=[[0], [0]], covariance_matrix=[[1, 0], [0, 1]])
        x20001 = state['x20001']
        p10000 = dist_x20001.log_pdf(x20001)
        dist_y20002 = dist.MultivariateNormal(mu=x20001, covariance_matrix=[[2, 0], [0, 2]])
        p10001 = dist_y20002.log_pdf([7, 7])
        logp = p10000 + p10001
        return logp

    @classmethod
    def gen_prior_samples(self):
        dist_x20001 = dist.MultivariateNormal(mu=[0, 0], covariance_matrix=[[1, 0], [0, 1]])
		# dist_x20001 = dist.MultivariateNormal(mu=[[0], [0]], covariance_matrix=[[1, 0], [0, 1]])
        x20001 = dist_x20001.sample()
        dist_y20002 = dist.MultivariateNormal(mu=x20001, covariance_matrix=[[2, 0], [0, 2]])
        y20002 = [7, 7]
        state = {}
        for _gv in self.gen_vars():
            state[_gv] = locals()[_gv]
        return state  # dictionary

    @classmethod
    def gen_vars(self):
        return ['x20001']
