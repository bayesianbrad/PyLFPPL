#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 21. Feb 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
from ..fe_clojure import ppl_clojure_forms as clj
from ..ppl_ast import *
from .ppl_clojure_lexer import ClojureLexer
from .ppl_clojure_parser import ClojureParser


#######################################################################################################################

class FopplParser(ClojureParser):

    def visit_loop(self, count, initial_data, function, *args):
        if not clj.is_integer(count):
            raise SyntaxError("loop requires an integer value as first argument")
        count = count.value
        initial_data = initial_data.visit(self)
        function = function.visit(self)
        args = [arg.visit(self) for arg in args]
        result = initial_data
        i = 0
        while i < count:
            result = AstCall(function, [AstValue(i), result] + args)
            i += 1
        return result


#######################################################################################################################

def parse(source):
    clj_ast = list(ClojureLexer(source))
    ppl_ast = FopplParser().visit(clj_ast)
    return ppl_ast
