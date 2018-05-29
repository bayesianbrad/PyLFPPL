#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 18. Nov 2017, Tobias Kohn
# 24. Jan 2018, Tobias Kohn
#
from importlib.abc import Loader as _Loader, MetaPathFinder as _MetaPathFinder
from .compilers import compile
import sys

_PATH = sys.path[0]

def compile_module(module, input_text):
    graph, expr = compile(input_text)
    module.model = graph.create_model(result_expr=expr)
    return module

class Clojure_Loader(_Loader):

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        with open(module.__name__) as input_file:
            input_text = ''.join(input_file.readlines())
            compile_module(module, input_text)

class Clojure_Finder(_MetaPathFinder):

    def find_module(self, fullname, path=None):
        if path is None:
            path = _PATH
        return self.find_spec(fullname, path)

    def find_spec(self, fullname, path, target = None):
        import os.path
        from importlib.machinery import ModuleSpec

        fullname = fullname.split(sep='.')[-1]

        if '.' in fullname:
            raise NotImplementedError()

        possible_locations = [
            '',
            'foppl-src/',
            'foppl_src/',
            'foppl-models/',
            'foppl_models/',
            'models',
            'examples/'
        ]
        for ext in ['.foppl', '.foppl.clj', '.foppl.py', '.clj']:
            for loc in possible_locations:
                name = loc + fullname + ext
                if os.path.exists(name):
                    return ModuleSpec(os.path.realpath(name), Clojure_Loader())
        return None

import sys
sys.meta_path.append(Clojure_Finder())
