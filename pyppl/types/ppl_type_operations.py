#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 19. Feb 2018, Tobias Kohn
# 19. Feb 2018, Tobias Kohn
#
from .ppl_types import *

#######################################################################################################################

def _binary_(left, right):
    return union(left, right)

def add(left, right):
    return _binary_(left, right)

def sub(left, right):
    return _binary_(left, right)

def mul(left, right):
    if left in String and right in Integer:
        return left
    elif left in Integer and right in String:
        return right
    return _binary_(left, right)

def div(left, right):
    return _binary_(left, right)

def idiv(left, right):
    return _binary_(left, right)

def mod(left, right):
    return _binary_(left, right)


#######################################################################################################################

def neg(item):
    return item

def pos(item):
    return item
