#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 01. Mar 2018, Tobias Kohn
# 15. Mar 2018, Tobias Kohn
#
from pyppl.ppl_ast import *

class MyVisitor(Visitor):
    """
    This is a visitor-template. Copy/Paste it into a new file and then change it according to your own needs!
    """

    def visit_attribute(self, node:AstAttribute):
        return self.visit_node(node)

    def visit_binary(self, node:AstBinary):
        return self.visit_node(node)

    def visit_body(self, node:AstBody):
        return self.visit_node(node)

    def visit_break(self, node: AstBreak):
        return self.visit_node(node)

    def visit_call(self, node: AstCall):
        return self.visit_node(node)

    def visit_compare(self, node: AstCompare):
        return self.visit_node(node)

    def visit_def(self, node: AstDef):
        return self.visit_node(node)

    def visit_dict(self, node: AstDict):
        return self.visit_node(node)

    def visit_for(self, node: AstFor):
        return self.visit_node(node)

    def visit_function(self, node: AstFunction):
        return self.visit_node(node)

    def visit_if(self, node: AstIf):
        return self.visit_node(node)

    def visit_import(self, node: AstImport):
        return self.visit_node(node)

    def visit_let(self, node: AstLet):
        return self.visit_node(node)

    def visit_list_for(self, node: AstListFor):
        return self.visit_node(node)

    def visit_observe(self, node: AstObserve):
        return self.visit_node(node)

    def visit_return(self, node: AstReturn):
        return self.visit_node(node)

    def visit_sample(self, node: AstSample):
        return self.visit_node(node)

    def visit_slice(self, node: AstSlice):
        return self.visit_node(node)

    def visit_subscript(self, node: AstSubscript):
        return self.visit_node(node)

    def visit_symbol(self, node: AstSymbol):
        return self.visit_node(node)

    def visit_unary(self, node: AstUnary):
        return self.visit_node(node)

    def visit_value(self, node: AstValue):
        return self.visit_node(node)

    def visit_value_vector(self, node: AstValueVector):
        return self.visit_node(node)

    def visit_vector(self, node: AstVector):
        return self.visit_node(node)

    def visit_while(self, node: AstWhile):
        return self.visit_node(node)
