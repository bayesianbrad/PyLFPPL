#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 15. Mar 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
from ast import copy_location as _cl
from ..ppl_ast import *

class VarSubstitutor(Visitor):

    def __init__(self, bindings:dict):
        self.bindings = bindings
        assert type(self.bindings) is dict
        assert all([isinstance(self.bindings[key], AstNode) for key in self.bindings])

    def parse_items(self, items:list):
        use_original = True
        result = []
        for item in items:
            n_item = self.visit(item)
            use_original = use_original and n_item is item
            result.append(n_item)
        if use_original:
            return items
        else:
            return result

    def visit_node(self, node: AstNode):
        return node

    def visit_attribute(self, node:AstAttribute):
        base = self.visit(node.base)
        if base is node.base:
            return node
        else:
            return _cl(AstAttribute(base, node.attr), node)

    def visit_binary(self, node:AstBinary):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        else:
            return _cl(AstBinary(left, node.op, right), node)

    def visit_body(self, node:AstBody):
        items = self.parse_items(node.items)
        if items is node.items:
            return node
        else:
            return _cl(makeBody(items), node)

    def visit_call(self, node: AstCall):
        args = self.parse_items(node.args)
        if args is node.args:
            return node
        else:
            return node.clone(args=args)

    def visit_compare(self, node: AstCompare):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        else:
            return _cl(AstCompare(left, node.op, right), node)

    def visit_def(self, node: AstDef):
        value = self.visit(node.value)
        if value is node.value:
            return node
        else:
            return _cl(AstDef(node.name, value), node)

    def visit_dict(self, node: AstDict):
        return self.visit_node(node)

    def visit_for(self, node: AstFor):
        return self.visit_node(node)

    def visit_function(self, node: AstFunction):
        return self.visit_node(node)

    def visit_if(self, node: AstIf):
        return self.visit_node(node)

    def visit_let(self, node: AstLet):
        return self.visit_node(node)

    def visit_list_for(self, node: AstListFor):
        return self.visit_node(node)

    def visit_observe(self, node: AstObserve):
        dist = self.visit(node.dist)
        value = self.visit(node.value)
        if dist is node.dist and value is node.value:
            return node
        else:
            return _cl(AstObserve(dist, value), node)

    def visit_return(self, node: AstReturn):
        value = self.visit(node.value)
        if value is node.value:
            return node
        else:
            return _cl(AstReturn(value), node)

    def visit_sample(self, node: AstSample):
        dist = self.visit(node.dist)
        if dist is node.dist:
            return node
        else:
            return _cl(AstSample(dist), node)

    def visit_slice(self, node: AstSlice):
        return self.visit_node(node)

    def visit_subscript(self, node: AstSubscript):
        return self.visit_node(node)

    def visit_symbol(self, node: AstSymbol):
        name = node.name
        if name in self.bindings:
            return self.visit(self.bindings[name])
        else:
            return node

    def visit_unary(self, node: AstUnary):
        item = self.visit(node.item)
        if item is node.item:
            return node
        else:
            return _cl(AstUnary(node.op, item), node)

    def visit_vector(self, node: AstVector):
        items = self.parse_items(node.items)
        if items is node.items:
            return node
        else:
            return _cl(makeVector(items), node)

    def visit_while(self, node: AstWhile):
        test = self.visit(node.test)
        body = self.visit(node.body)
        if test is node.test and body is node.body:
            return node
        else:
            return _cl(AstWhile(test, body), node)
