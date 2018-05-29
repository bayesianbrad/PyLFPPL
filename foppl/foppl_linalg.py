#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 23. Jan 2018, Tobias Kohn
# 23. Jan 2018, Tobias Kohn
#
import numpy as np

def _to_numpy(*items):
    result = [(np.array(item) if type(item) is list else item) for item in items]
    if len(result) == 1:
        return result[0]
    else:
        return tuple(result)


def add(a, b):
    a, b = _to_numpy(a, b)
    return a + b

def sub(a, b):
    a, b = _to_numpy(a, b)
    return a - b

def mul(a, b):
    a, b = _to_numpy(a, b)
    return a * b

def div(a, b):
    a, b = _to_numpy(a, b)
    return a / b

def exp(a):
    return np.exp(_to_numpy(a))

def ge(a, b):
    a, b = _to_numpy(a, b)
    return (a >= b).astype(int)

def gt(a, b):
    a, b = _to_numpy(a, b)
    return (a > b).astype(int)

def le(a, b):
    a, b = _to_numpy(a, b)
    return (a <= b).astype(int)

def lt(a, b):
    a, b = _to_numpy(a, b)
    return (a < b).astype(int)

def eq(a, b):
    a, b = _to_numpy(a, b)
    return (a == b).astype(int)

def mmul(a, b):
    a, b = _to_numpy(a, b)
    return np.dot(a, b)
