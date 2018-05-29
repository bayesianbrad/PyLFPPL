#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 12. Mar 2018, Tobias Kohn
# 12. Mar 2018, Tobias Kohn
#
from importlib import import_module

def namespace_from_module(module_name: str):
    module = import_module(module_name)
    if module is not None:
        return module.__name__, [name for name in dir(module) if not name.startswith('_')]
    else:
        return None, []
