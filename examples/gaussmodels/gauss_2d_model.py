#
# Generated: 2018-01-14 11:08:49.131417
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
	  x20001, x20002, y20003, y20004
	Arcs A:
	  (x20002, y20004), (x20001, y20003)
	Conditional densities C:
	  x20001 -> dist.Normal(mu=1.0, sigma=2.23606797749979)
	  y20003 -> dist.Normal(mu=x20001, sigma=1.4142135623730951)
	  x20002 -> dist.Normal(mu=1.0, sigma=2.23606797749979)
	  y20004 -> dist.Normal(mu=x20002, sigma=1.4142135623730951)
	Observed values O:
	  y20003 -> 7.0
	  y20004 -> 7.0
	"""
	vertices = {'y20004', 'x20001', 'x20002', 'y20003'}
	arcs = {('x20002', 'y20004'), ('x20001', 'y20003')}
	names = {'x20001': 'x1', 'x20002': 'x2'}
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
		return [ 'x20002']

	@classmethod
	def gen_if_vars(self):
		return []

	@classmethod
	def gen_pdf(self, state):
		dist_x20001 = dist.Normal(mu=1.0, sigma=2.23606797749979)
		x20001 = state['x20001']
		p10000 = dist_x20001.log_pdf(x20001)
		dist_x20002 = dist.Normal(mu=1.0, sigma=2.23606797749979)
		x20002 = state['x20002']
		p10001 = dist_x20002.log_pdf(x20002)
		dist_y20003 = dist.Normal(mu=x20001, sigma=1.4142135623730951)
		p10002 = dist_y20003.log_pdf(7.0)
		dist_y20004 = dist.Normal(mu=x20002, sigma=1.4142135623730951)
		p10003 = dist_y20004.log_pdf(7.0)
		logp = p10000 + p10001 + p10002 + p10003
		return logp

	@classmethod
	def gen_prior_samples(self):
		dist_x20001 = dist.Normal(mu=1.0, sigma=2.23606797749979)
		x20001 = dist_x20001.sample()
		dist_x20002 = dist.Normal(mu=1.0, sigma=2.23606797749979)
		x20002 = dist_x20002.sample()
		dist_y20003 = dist.Normal(mu=x20001, sigma=1.4142135623730951)
		y20003 = 7.0
		dist_y20004 = dist.Normal(mu=x20002, sigma=1.4142135623730951)
		y20004 = 7.0
		state = {}
		for _gv in self.gen_vars():
			state[_gv] = locals()[_gv]
		return state  # dictionary

	@classmethod
	def gen_vars(self):
		return ['x20001', 'x20002']
