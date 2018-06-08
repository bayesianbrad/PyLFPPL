#
# Generated: 2018-01-15 12:50:30.363190
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
	  c20002, cond_20003, f20004, x20001, y20005, y20006
	Arcs A:
	  (f20004, c20002), (y20006, c20002), (f20004, cond_20003), (cond_20003, y20006), (x20001, c20002), (y20005, c20002), (cond_20003, c20002), (cond_20003, y20005), (x20001, f20004)
	Conditional densities C:
	  x20001 -> dist.Normal(mu=0, sigma=1.0)
	  f20004 -> -x20001
	  cond_20003 -> (f20004 >= 0).data[0]
	  y20005 -> dist.Normal(mu=1, sigma=1.0)
	  y20006 -> dist.Normal(mu=-1, sigma=1.0)
	  c20002 -> y20005 if not cond_20003 else y20006
	Observed values O:
	  y20005 -> 1
	  y20006 -> 1
	"""
	vertices = {'y20005', 'c20002', 'y20006', 'x20001', 'cond_20003', 'f20004'}
	arcs = {('f20004', 'c20002'), ('y20006', 'c20002'), ('f20004', 'cond_20003'), ('cond_20003', 'y20006'), ('x20001', 'c20002'), ('y20005', 'c20002'), ('cond_20003', 'c20002'), ('cond_20003', 'y20005'), ('x20001', 'f20004')}
	names = {'x20001': 'x'}
	cond_functions = {
	  'cond_20003': 'f20004',
	  'f20004': lambda state: -state['x20001']
	}

	@classmethod
	def get_vertices(self):
		return list(self.vertices)

	@classmethod
	def get_arcs(self):
		return list(self.arcs)

	@classmethod
	def gen_all_keys(self):
		return ['c20002', 'cond_20003', 'f20004', 'x20001']

	@classmethod
	def gen_cond_vars(self):
		return ['cond_20003']

	@classmethod
	def gen_cont_vars(self):
		return []

	@classmethod
	def gen_disc_vars(self):
		return []

	@classmethod
	def gen_if_functions(self):
		return ['f20004']

	@classmethod
	def gen_if_vars(self):
		return ['x20001']

	@classmethod
	def gen_pdf(self, state):
		dist_x20001 = dist.Normal(mu=0, sigma=1.0)
		x20001 = state['x20001']
		p10000 = dist_x20001.log_pdf(x20001)
		f20004 = -x20001
		cond_20003 = state['cond_20003']
		dist_y20005 = dist.Normal(mu=1, sigma=1.0)
		p10001 = dist_y20005.log_pdf(1) if not cond_20003 else 0
		dist_y20006 = dist.Normal(mu=-1, sigma=1.0)
		p10002 = dist_y20006.log_pdf(1) if cond_20003 else 0
		logp = p10000 + p10001 + p10002
		return logp

	@classmethod
	def gen_prior_samples(self):
		dist_x20001 = dist.Normal(mu=0, sigma=1.0)
		x20001 = dist_x20001.sample()
		f20004 = -x20001
		cond_20003 = (f20004 >= 0).data[0]
		dist_y20005 = dist.Normal(mu=1, sigma=1.0)
		y20005 = 1
		dist_y20006 = dist.Normal(mu=-1, sigma=1.0)
		y20006 = 1
		c20002 = y20005 if not cond_20003 else y20006
		state = {}
		for _gv in self.gen_all_keys():
			state[_gv] = locals()[_gv]
		return state  # dictionary

	@classmethod
	def gen_vars(self):
		return ['x20001']
