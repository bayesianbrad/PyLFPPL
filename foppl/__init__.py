#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
##
# 19. Dec 2017, Tobias Kohn
# 01. Feb 2018, Tobias Kohn
#
class Options(object):
    """
    This class provides flags and general options to control the compilation process.

    `eager_conditionals`:
        Controls whether conditional statements (`if`-expressions) should be evaluated eagerly or lazily.
        _At the moment, only eager evaluation is supported._

    `uniform_conditionals`:
        If this flag is set to `True`, the compiler will transform all comparisons (except for equality) to be
        in the form `X >= 0`. For instance, `x < 5` will thus be transformed to `not (x-5 >= 0)`.

    `conditional_suffix`:
        A string suffix that is appended to conditional variables.

    `debug`:
        Print out additional information, e. g., about the nodes in the graph.

    `de_vectorize`
        When set to `True`, the compiler tries to unpack all vectors and lists and apply the operations on
        scalars only. When set to `False`, the compiler will leave vectors and try to avoid unpacking any
        of them.

    `log_file`
        If this specifies a file name, a debug print of the generated model will be written to the file.
        Otherwise the field should be `None`.

    `require_unique_names`
        If `True`, each sample inside the code must be unique and no duplicates are allowed.
    """

    eager_conditionals = True

    uniform_conditionals = True

    debug = False

    de_vectorize = False

    log_file = None

    # Some models with loops (e.g. neural_net_model) do not compile with this flag set on
    require_unique_names = False


class Config(object):

    conditional_suffix = '.data[0]'

    dist_param_wrapper = None

    dist_use_keyword_parameters = True

    sample_method = '.sample()'

    log_pdf_method = '.log_prob({})'


# Stubs to make the Python-IDE happy

def sample(distr): return 0

def observe(distr, value): pass

def binomial(p): pass

def categorical(ps): pass

def normal(mu, sigma): pass

def interleave(a, b): return a

def load(source): return [1, 2, 3]

class matrix(object):

    @staticmethod
    def add(*args): return [1, 2, 3]
    @staticmethod
    def sub(*args): return [1, 2, 3]
    @staticmethod
    def mul(*args): return [1, 2, 3]
    @staticmethod
    def div(*args): return [1, 2, 3]

    @staticmethod
    def ge(*args): return [1, 0, 1]
    @staticmethod
    def gt(*args): return [1, 0, 1]
    @staticmethod
    def le(*args): return [1, 0, 1]
    @staticmethod
    def lt(*args): return [1, 0, 1]

    @staticmethod
    def exp(arg): return [1, 2, 3]

    @staticmethod
    def mmul(*args): return [1, 2, 3]
