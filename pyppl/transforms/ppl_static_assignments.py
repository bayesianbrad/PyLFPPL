#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Mar 2018, Tobias Kohn
# 21. Mar 2018, Tobias Kohn
#
from ..ppl_ast import *
from ..aux.ppl_transform_visitor import TransformVisitor
from ast import copy_location as _cl


class Symbol(object):

    def __init__(self, name):
        self.name = name
        self.counter = 0

    def get_new_instance(self):
        self.counter += 1
        return self.get_current_instance()

    def get_current_instance(self):
        if self.counter == 1:
            return self.name
        else:
            return self.name + str(self.counter)


class SymbolScope(object):

    def __init__(self, prev, items=None, is_loop:bool=False):
        self.prev = prev
        self.bindings = {}
        self.items = items
        self.is_loop = is_loop

    def get_current_symbol(self, name: str):
        if name in self.bindings:
            return self.bindings[name]
        elif self.prev is not None:
            return self.prev.get_current_symbol(name)
        else:
            return name

    def has_current_symbol(self, name: str):
        if name in self.bindings:
            return True
        elif self.prev is not None:
            return self.prev.has_current_symbol(name)
        else:
            return False

    def set_current_symbol(self, name: str, instance_name: str):
        self.bindings[name] = instance_name

    def append(self, item):
        if self.items is not None:
            self.items.append(item)
            return True
        else:
            return False


class StaticAssignments(TransformVisitor):

    def __init__(self):
        super().__init__()
        self.symbols = {}
        self.symbol_scope = SymbolScope(None)

    def new_symbol_instance(self, name: str):
        if name not in self.symbols:
            self.symbols[name] = Symbol(name)
        result = self.symbols[name].get_new_instance()
        self.symbol_scope.set_current_symbol(name, result)
        return result

    def access_symbol(self, name: str):
        result = self.symbol_scope.get_current_symbol(name)
        return result

    def has_symbol(self, name: str):
        return self.symbol_scope.has_current_symbol(name)

    def begin_scope(self, items=None, is_loop:bool=False):
        self.symbol_scope = SymbolScope(self.symbol_scope, items, is_loop)

    def end_scope(self):
        scope = self.symbol_scope
        self.symbol_scope = scope.prev
        return scope.bindings

    def append_to_body(self, item: AstNode):
        return self.symbol_scope.append(item)

    def is_loop_scope(self):
        return self.symbol_scope.is_loop

    def split_body(self, node: AstNode):
        if isinstance(node, AstBody):
            if len(node) == 0:
                return None, AstValue(None)
            elif len(node) == 1:
                return None, node[0]
            else:
                return node.items[:-1], node.items[-1]
        else:
            return None, node

    def visit_and_split(self, node: AstNode):
        return self.split_body(self.visit(node))

    def visit_in_scope(self, node: AstNode, is_loop:bool=False):
        items = []
        self.begin_scope(items, is_loop)
        if isinstance(node, AstBody):
            for item in node.items:
                items.append(self.visit(item))
        else:
            items.append(self.visit(node))
        result = _cl(makeBody(items), node)
        symbols = self.end_scope()
        return symbols, result


    def visit_attribute(self, node:AstAttribute):
        prefix, base = self.visit_and_split(node.base)
        if prefix is not None:
            return makeBody(prefix, node.clone(base=base))
        if base is node.base:
            return node
        else:
            return node.clone(base=base)

    def visit_binary(self, node:AstBinary):
        prefix_l, left = self.visit_and_split(node.left)
        prefix_r, right = self.visit_and_split(node.right)
        if prefix_l is not None and prefix_r is not None:
            prefix = prefix_l + prefix_r
            return makeBody(prefix, node.clone(left=left, right=right))
        elif prefix_l is not None:
            return makeBody(prefix_l, node.clone(left=left, right=right))
        elif prefix_r is not None:
            return makeBody(prefix_r, node.clone(left=left, right=right))

        if left is node.left and right is node.right:
            return node
        else:
            return node.clone(left=left, right=right)

    def _visit_call(self, node: AstCall):
        prefix = []
        args = []
        for item in node.args:
            p, a = self.visit_and_split(item)
            if p is not None:
                prefix += p
            args.append(a)

        if len(prefix) > 0:
            return makeBody(prefix, node.clone(args=args))
        else:
            return node.clone(args=args)

    def visit_call(self, node: AstCall):
        tmp = generate_temp_var()
        result = AstDef(tmp, self._visit_call(node))
        if self.append_to_body(result):
            return AstSymbol(tmp)
        else:
            return makeBody(result, AstSymbol(tmp))

    def visit_call_range(self, node: AstCall):
        if node.arg_count == 1 and is_integer(node.args[0]):
            return makeVector(list(range(node.args[0].value)))
        else:
            return self.visit_call(node)

    def visit_compare(self, node: AstCompare):
        prefix_l, left = self.visit_and_split(node.left)
        prefix_r, right = self.visit_and_split(node.right)
        if node.second_right is not None:
            prefix_s, second_right = self.visit_and_split(node.second_right)
        else:
            prefix_s, second_right = None, None

        if prefix_l is not None or prefix_r is not None or prefix_s is not None:
            prefix = prefix_l if prefix_l is not None else []
            if prefix_r is not None: prefix += prefix_r
            if prefix_s is not None: prefix += prefix_s
            return makeBody(prefix, node.clone(left=left, right=right, second_right=second_right))

        if left is node.left and right is node.right and second_right is node.second_right:
            return node
        else:
            return node.clone(left=left, right=right, second_right=second_right)

    def visit_def(self, node: AstDef):
        if isinstance(node.value, AstObserve):
            # We can never assign an observe to something!
            result = [self.visit(node.value),
                      self.visit(node.clone(value=AstValue(None)))]
            return makeBody(result)

        elif isinstance(node.value, AstSample):
            # We need to handle this as a special case in order to avoid an infinite loop
            value = self._visit_sample(node.value)
            name = self.new_symbol_instance(node.name)
            return node.clone(name=name, value=value)

        elif isinstance(node.value, AstCall):
            result = self._visit_call(node.value)
            name = self.new_symbol_instance(node.name)
            return node.clone(name=name, value=result)

        prefix, value = self.visit_and_split(node.value)
        if prefix is not None:
            return makeBody(prefix, self.visit(node.clone(value=value)))

        elif isinstance(value, AstFunction):
            return AstBody([])

        name = self.new_symbol_instance(node.name)
        if name is node.name and value is node.value:
            return node
        else:
            return node.clone(name=name, value=value)

    def visit_dict(self, node: AstDict):
        prefix = []
        items = {}
        for key in node.items:
            item = node.items[key]
            p, i = self.visit_and_split(item)
            if p is not None:
                prefix += p
            items[key] = i
        if len(prefix) > 0:
            return makeBody(prefix, AstDict(items))
        else:
            return AstDict(items)

    def visit_for(self, node: AstFor):
        prefix, source = self.visit_and_split(node.source)
        if prefix is not None:
            return self.visit(makeBody(prefix, node.clone(source=source)))

        if is_vector(source):
            result = []
            for item in source:
                result.append(AstLet(node.target, item, node.body))
            return self.visit(makeBody(result))

        _, body = self.visit_in_scope(node.body, is_loop=True)
        if source is node.source and body is node.body:
            return node
        else:
            return node.clone(source=source, body=body)

    def visit_if(self, node: AstIf):

        def phi(key, cond, left, right):
            return AstDef(key, AstIf(cond, AstSymbol(left), AstSymbol(right)))

        prefix, test = self.visit_and_split(node.test)
        if prefix is not None:
            return makeBody(prefix, self.visit(node.clone(test=test)))

        if isinstance(test, AstValue):
            if test.value is True:
                return self.visit(node.if_node)
            elif test.value is False or test.value is None:
                return self.visit(node.else_node)

        if_symbols, if_node = self.visit_in_scope(node.if_node)
        else_symbols, else_node = self.visit_in_scope(node.else_node)
        keys = set.union(set(if_symbols.keys()), set(else_symbols.keys()))
        if len(keys) == 0:
            if test is node.test and if_node is node.if_node and else_node is node.else_node:
                return node
            else:
                return node.clone(test=test, if_node=if_node, else_node=else_node)
        else:
            result = []
            if not isinstance(test, AstSymbol):
                tmp = generate_temp_var()
                result.append(AstDef(tmp, test))
                test = AstSymbol(tmp)
            result.append(node.clone(test=test, if_node=if_node, else_node=else_node))
            for key in keys:
                if key in if_symbols and key in else_symbols:
                    result.append(phi(self.new_symbol_instance(key), test, if_symbols[key], else_symbols[key]))
                elif not self.has_symbol(key):
                    pass
                elif key in if_symbols:
                    result.append(phi(self.new_symbol_instance(key), test, if_symbols[key], self.access_symbol(key)))
                elif key in else_symbols:
                    result.append(phi(self.new_symbol_instance(key), test, self.access_symbol(key), else_symbols[key]))
            return makeBody(result)

    def visit_let(self, node: AstLet):
        if node.target == '_':
            result = makeBody(node.source, node.body)
        else:
            result = makeBody(AstDef(node.target, node.source), node.body)
        return self.visit(result)

    def visit_list_for(self, node: AstListFor):
        prefix, source = self.visit_and_split(node.source)
        if prefix is not None:
            return makeBody(prefix, self.visit(node.clone(source=source)))

        if is_vector(source):
            result = []
            for item in source:
                result.append(AstLet(node.target, item, node.expr))
            return self.visit(makeVector(result))

        if isinstance(node.expr, AstSample):
            expr = self._visit_sample(node.expr)
        elif isinstance(node.expr, AstCall):
            expr = self._visit_call(node.expr)
        else:
            expr = self.visit(node.expr)

        if source is node.source and expr is node.expr:
            return node
        else:
            return node.clone(source=source, expr=expr)

    def visit_observe(self, node: AstObserve):
        prefix, dist = self.visit_and_split(node.dist)
        if prefix is not None:
            return makeBody(prefix, self.visit(node.clone(dist=dist)))
        prefix, value = self.visit_and_split(node.value)
        if prefix is not None:
            return makeBody(prefix, node.clone(value=value))
        if dist is node.dist and value is node.value:
            return node
        else:
            return node.clone(dist=dist, value=value)

    def _visit_sample(self, node: AstSample):
        prefix, dist = self.visit_and_split(node.dist)
        if prefix is not None:
            return makeBody(prefix, node.clone(dist=dist))
        if dist is node.dist:
            return node
        else:
            return node.clone(dist=dist)

    def visit_sample(self, node: AstSample):
        tmp = generate_temp_var()
        assign = AstDef(tmp, self._visit_sample(node))
        if self.append_to_body(assign):
            return AstSymbol(tmp)
        else:
            return makeBody([assign, AstSymbol(tmp)])

    def visit_symbol(self, node: AstSymbol):
        name = self.access_symbol(node.name)
        if name != node.name:
            return node.clone(name=name)
        else:
            return node

    def visit_unary(self, node: AstUnary):
        prefix, item = self.visit_and_split(node.item)
        if prefix is not None:
            return makeBody(prefix, node.clone(item=item))
        if item is node.item:
            return node
        else:
            return node.clone(item=item)

    def visit_vector(self, node: AstVector):
        prefix = []
        items = []
        for item in node.items:
            p, i = self.visit_and_split(item)
            if p is not None:
                prefix += p
            items.append(i)
        if len(prefix) > 0:
            return makeBody(prefix, makeVector(items))
        else:
            return makeVector(items)

    def visit_while(self, node: AstWhile):
        prefix, test = self.visit_and_split(node.test)
        if prefix is not None:
            return makeBody(prefix, self.visit(node.clone(test=test)))

        _, body = self.visit_in_scope(node.body, is_loop=True)
        if test is node.test and body is node.body:
            return node
        else:
            return node.clone(test=test, body=body)
