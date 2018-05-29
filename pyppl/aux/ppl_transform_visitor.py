#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 15. Mar 2018, Tobias Kohn
# 11. May 2018, Tobias Kohn
#
from ..ppl_ast import *
from ast import copy_location as _cl

class TransformVisitor(ScopedVisitor):

    def do_visit_dict(self, items:dict):
        result = {}
        for key in items:
            n_item = self.visit(items[key])
            if n_item is not items[key]:
                result[key] = n_item
        if len(result) > 0:
            return items.copy().update(result)
        else:
            return items

    def do_visit_items(self, items:list):
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
            return node.clone(base=base)

    def visit_binary(self, node:AstBinary):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        else:
            return node.clone(left=left, right=right)

    def visit_body(self, node:AstBody):
        items = self.do_visit_items(node.items)
        if items is node.items:
            return node
        else:
            return _cl(makeBody(items), node)

    def visit_call(self, node: AstCall):
        function = self.visit(node.function)
        args = self.do_visit_items(node.args)
        if function is node.function and args is node.args:
            return node
        else:
            return node.clone(function=function, args=args)

    def visit_compare(self, node: AstCompare):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is node.left and right is node.right:
            return node
        else:
            return node.clone(left=left, right=right)

    def visit_def(self, node: AstDef):
        value = self.visit(node.value)
        if value is node.value:
            return node
        else:
            return node.clone(value=value)

    def visit_dict(self, node: AstDict):
        items = self.do_visit_dict(node.items)
        if items is node.items:
            return node
        else:
            return node.clone(items=items)

    def visit_for(self, node: AstFor):
        source = self.visit(node.source)
        body = self.visit(node.body)
        if source is node.source and body is node.body:
            return node
        else:
            return node.clone(source=source, body=body)

    def visit_function(self, node: AstFunction):
        body = self.visit(node.body)
        if body is node.body:
            return node
        else:
            return node.clone(body=body)

    def visit_if(self, node: AstIf):
        test = self.visit(node.test)
        if_node = self.visit(node.if_node)
        else_node = self.visit(node.else_node)
        if test is node.test and if_node is node.if_node and else_node is node.else_node:
            return node
        else:
            return node.clone(test=test, if_node=if_node, else_node=else_node)

    def visit_let(self, node: AstLet):
        source = self.visit(node.source)
        body = self.visit(node.body)
        if source is node.source and body is node.body:
            return node
        else:
            return node.clone(source=source, body=body)

    def visit_list_for(self, node: AstListFor):
        source = self.visit(node.source)
        expr = self.visit(node.expr)
        if source is node.source and expr is node.expr:
            return node
        else:
            return node.clone(source=source, expr=expr)

    def visit_observe(self, node: AstObserve):
        dist = self.visit(node.dist)
        value = self.visit(node.value)
        if dist is node.dist and value is node.value:
            return node
        else:
            return node.clone(dist=dist, value=value)

    def visit_return(self, node: AstReturn):
        value = self.visit(node.value)
        if value is node.value:
            return node
        else:
            return node.clone(value=value)

    def visit_sample(self, node: AstSample):
        dist = self.visit(node.dist)
        if dist is node.dist:
            return node
        else:
            return node.clone(dist=dist)

    def visit_slice(self, node: AstSlice):
        base = self.visit(node.base)
        start = self.visit(node.start)
        stop = self.visit(node.stop)
        if base is node.base and start is node.start and stop is node.stop:
            return node
        else:
            return node.clone(base=base, start=start, stop=stop)

    def visit_subscript(self, node: AstSubscript):
        base = self.visit(node.base)
        index = self.visit(node.index)
        if base is node.base and index is node.index:
            return node
        else:
            return node.clone(base=base, index=index)

    def visit_unary(self, node: AstUnary):
        item = self.visit(node.item)
        if item is node.item:
            return node
        else:
            return node.clone(item=item)

    def visit_vector(self, node: AstVector):
        items = self.do_visit_items(node.items)
        if items is node.items:
            return node
        else:
            return node.clone(items=items)

    def visit_while(self, node: AstWhile):
        test = self.visit(node.test)
        body = self.visit(node.body)
        if test is node.test and body is node.body:
            return node
        else:
            return node.clone(test=test, body=body)
