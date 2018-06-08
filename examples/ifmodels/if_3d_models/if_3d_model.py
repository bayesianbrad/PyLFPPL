#
# Generated: 2018-01-17 15:44:40.201786
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
	  c20002, cond_20003, f20004, x20001, x20005, x20007, y20006, y20008
	Arcs A:
	  (cond_20003, c20002), (y20006, c20002), (x20007, y20008), (cond_20003, x20005), (cond_20003, y20008), (f20004, cond_20003), (f20004, c20002), (x20005, y20006), (cond_20003, x20007), (x20005, c20002), (x20001, c20002), (y20008, c20002), (x20007, c20002), (x20001, f20004), (cond_20003, y20006)
	Conditional densities C:
	  x20001 -> dist.Normal(mu=0, sigma=1.0)
	  f20004 -> -x20001
	  cond_20003 -> (f20004 >= 0).data[0]
	  x20005 -> dist.Normal(mu=0, sigma=1.0)
	  y20006 -> dist.Normal(mu=x20005, sigma=1.4142135623730951)
	  x20007 -> dist.Normal(mu=0, sigma=1.0)
	  y20008 -> dist.Normal(mu=x20007, sigma=1.4142135623730951)
	  c20002 -> y20006 if not cond_20003 else y20008
	Observed values O:
	  y20006 -> 10
	  y20008 -> 10
	"""
	vertices = {'x20005', 'f20004', 'c20002', 'y20006', 'cond_20003', 'x20001', 'x20007', 'y20008'}
	arcs = {('cond_20003', 'c20002'), ('y20006', 'c20002'), ('x20007', 'y20008'), ('cond_20003', 'x20005'), ('cond_20003', 'y20008'), ('f20004', 'cond_20003'), ('f20004', 'c20002'), ('x20005', 'y20006'), ('cond_20003', 'x20007'), ('x20005', 'c20002'), ('x20001', 'c20002'), ('y20008', 'c20002'), ('x20007', 'c20002'), ('x20001', 'f20004'), ('cond_20003', 'y20006')}
	names = {'x20001': 'x1', 'x20005': 'x2', 'x20007': 'x3'}
	cond_functions = {
	  'cond_20003': 'f20004',
	  'f20004': lambda state: -state['x20001']
	}
	disc_dists = {}

	@classmethod
	def get_vertices(self):
		return list(self.vertices)

	@classmethod
	def get_arcs(self):
		return list(self.arcs)

	@classmethod
	def get_discrete_distribution(self, name):
		return self.disc_dists

	@classmethod
	def get_cond_function(self, name):
		f = self.cond_functions[name]
		if type(f) is str and f in self.cond_functions:
			f = self.cond_functions[f]
		return f

	@classmethod
	def gen_all_keys(self):
		return ['c20002', 'cond_20003', 'f20004', 'x20001', 'x20005', 'x20007']

	@classmethod
	def gen_cond_vars(self):
		return ['cond_20003']

	@classmethod
	def gen_cont_vars(self):
		return ['x20005', 'x20007']

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
		cond_20003 = (f20004 >= 0).data[0]
		dist_x20005 = dist.Normal(mu=0, sigma=1.0)
		x20005 = state['x20005']
		p10001 = dist_x20005.log_pdf(x20005)
		dist_x20007 = dist.Normal(mu=0, sigma=1.0)
		x20007 = state['x20007']
		p10002 = dist_x20007.log_pdf(x20007)
		dist_y20006 = dist.Normal(mu=x20005, sigma=1.4142135623730951)
		p10003 = dist_y20006.log_pdf(10) if not cond_20003 else 0
		dist_y20008 = dist.Normal(mu=x20007, sigma=1.4142135623730951)
		p10004 = dist_y20008.log_pdf(10) if cond_20003 else 0
		_lcls = locals()
		for key in state:
			if key in _lcls:
				state[key] = _lcls[key]
		logp = p10000 + p10001 + p10002 + p10003 + p10004
		return logp

	@classmethod
	def gen_prior_samples(self):
		dist_x20001 = dist.Normal(mu=0, sigma=1.0)
		x20001 = dist_x20001.sample()
		f20004 = -x20001
		cond_20003 = (f20004 >= 0).data[0]
		dist_x20005 = dist.Normal(mu=0, sigma=1.0)
		x20005 = dist_x20005.sample()
		dist_x20007 = dist.Normal(mu=0, sigma=1.0)
		x20007 = dist_x20007.sample()
		dist_y20006 = dist.Normal(mu=x20005, sigma=1.4142135623730951)
		y20006 = 10
		dist_y20008 = dist.Normal(mu=x20007, sigma=1.4142135623730951)
		y20008 = 10
		c20002 = y20006 if not cond_20003 else y20008
		state = {}
		for _gv in self.gen_all_keys():
			state[_gv] = locals()[_gv]
		return state  # dictionary

	@classmethod
	def gen_vars(self):
		return ['x20001', 'x20005', 'x20007']
