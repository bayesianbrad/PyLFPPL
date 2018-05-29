#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 09. Mar 2018, Tobias Kohn
# 23. Mar 2018, Tobias Kohn
#
from ast import copy_location as _cl
from ..ppl_ast import *
from ..ppl_ast_annotators import get_info
from ..ppl_namespaces import namespace_from_module


class RawSimplifier(ScopedVisitor):

    def __init__(self, symbols:dict):
        super().__init__()
        self.imports = set()
        for key in symbols:
            self.define(key, AstSymbol(symbols[key], predef=True))

    def split_expr(self, node:AstNode):
        if node is None:
            return None
        elif isinstance(node, AstBody):
            if len(node) == 0:
                return [], AstValue(None)
            elif len(node) == 1:
                return [], node[0]
            else:
                return node.items[:-1], node.items[-1]
        elif isinstance(node, AstCall) and not node.is_builtin:
            tmp = generate_temp_var()
            return [AstDef(tmp, node, global_context=False)], AstSymbol(tmp)
        else:
            return [], node

    def _visit_expr(self, node:AstNode):
        return self.split_expr(self.visit(node))


    def visit_attribute(self, node:AstAttribute):
        base = self.visit(node.base)
        if isinstance(base, AstNamespace):
            if node.attr in base.bindings:
                return base.bindings[node.attr]
            else:
                return AstSymbol("{}.{}".format(base.name, node.attr))
        elif base is node.base:
            return node
        else:
            return node.clone(base=base)

    def visit_binary(self, node:AstBinary):
        l_prefix, left = self._visit_expr(node.left)
        r_prefix, right = self._visit_expr(node.right)
        prefix = l_prefix + r_prefix

        if left is node.left and right is node.right:
            return node
        else:
            prefix.append(AstBinary(left, node.op, right))
            return _cl(makeBody(prefix), node)

    def visit_body(self, node:AstBody):
        items = [self.visit(item) for item in node.items]

        i = len(items)-1
        while i >= 0:
            item = items[i]
            if isinstance(item, AstIf):
                if has_return(item.if_node) and not has_return(item.else_node):
                    items[i] = self.visit(AstIf(item.test, item.if_node, makeBody(item.else_node, items[i+1:])))
                    items = items[:i+1]
                if has_return(item.else_node) and not has_return(item.if_node):
                    items[i] = self.visit(AstIf(item.test, makeBody(item.if_node, items[i+1:]).item.else_node))
                    items = items[:i+1]
            i -= 1

        return _cl(makeBody(items), node)

    def visit_call(self, node: AstCall):
        if node.arg_count > 0:
            function = self.visit(node.function)
            prefix = []
            args = []
            for arg in node.args:
                p, a = self._visit_expr(arg)
                prefix += p
                args.append(a)
            return makeBody(prefix, node.clone(function=function, args=args))
        else:
            function = self.visit(node.function)
            if function is node.function:
                return node
            else:
                return node.clone(function=function)

    def visit_compare(self, node: AstCompare):
        l_prefix, left = self._visit_expr(node.left)
        r_prefix, right = self._visit_expr(node.right)
        prefix = l_prefix + r_prefix
        if node.second_right is not None:
            s_prefix, sec_right = self._visit_expr(node.second_right)
            prefix += s_prefix
        else:
            sec_right = None

        if left is node.left and right is node.right and sec_right is node.second_right:
            return node
        else:
            prefix.append(AstCompare(left, node.op, right, node.second_op, node.second_right))
            return _cl(makeBody(prefix), node)

    def visit_def(self, node: AstDef):
        if getattr(node.value, 'original_name', None) is None:
            node.value.original_name = node.name
        value = self.visit(node.value)
        if value is node.value:
            return node
        else:
            return node.clone(value=value)

    def visit_dict(self, node: AstDict):
        if len(node) > 0:
            prefix = []
            result = {}
            for key in node.items:
                p, i = self.visit(node.items[key])
                prefix += p
                result[key] = i
            return _cl(makeBody(prefix, AstDict(result)), node)
        else:
            return node

    def visit_for(self, node: AstFor):
        prefix, source = self._visit_expr(node.source)
        body = self.visit(node.body)
        target = node.target if node.target in get_info(body).free_vars else '_'
        if target is node.target and source is node.source and body is node.body:
            return node
        else:
            return _cl(makeBody(prefix, AstFor(target, source, body, original_target=node.original_target)), node)

    def visit_function(self, node: AstFunction):
        with self.create_scope():
            body = self.visit(node.body)
        if body is node.body:
            return node
        else:
            return node.clone(body=body)

    def visit_if(self, node: AstIf):
        prefix, test = self._visit_expr(node.test)
        if_node = self.visit(node.if_node)
        else_node = self.visit(node.else_node)

        if isinstance(if_node, AstReturn):
            if isinstance(else_node, AstReturn):
                return _cl(makeBody(prefix, AstReturn(AstIf(test, if_node.value, else_node.value))), node)
            elif is_non_empty_body(else_node) and else_node.last_is_return:
                tmp = generate_temp_var()
                if_node = _cl(AstDef(tmp, if_node.value, global_context=False), if_node)
                else_node = _cl(makeBody(else_node.items[-1], AstDef(tmp, else_node.items[-1].value, global_context=False)), else_node)
                return _cl(makeBody(prefix, AstIf(test, if_node, else_node), AstReturn(AstSymbol(tmp))), node)

        elif is_non_empty_body(if_node) and if_node.last_is_return:
            if isinstance(else_node, AstReturn):
                tmp = generate_temp_var()
                if_node = _cl(makeBody(if_node.items[:-1], AstDef(tmp, if_node.items[-1].value, global_context=False)), if_node)
                else_node = _cl(AstDef(tmp, else_node.value, global_context=False), else_node)
                return _cl(makeBody(prefix, AstIf(test, if_node, else_node), AstReturn(AstSymbol(tmp))), node)
            elif is_non_empty_body(else_node) and else_node.last_is_return:
                tmp = generate_temp_var()
                if_node = _cl(makeBody(if_node.items[:-1], AstDef(tmp, if_node.items[-1].value, global_context=False)), if_node)
                else_node = _cl(makeBody(else_node.items[:-1], AstDef(tmp, else_node.items[-1].value, global_context=False)), else_node)
                return _cl(makeBody(prefix, AstIf(test, if_node, else_node), AstReturn(AstSymbol(tmp))), node)

        if test is node.test and if_node is node.if_node and else_node is node.else_node:
            return node
        else:
            return _cl(makeBody(prefix, AstIf(test, if_node, else_node)), node)

    def visit_import(self, node: AstImport):
        module_name, names = namespace_from_module(node.module_name)
        if node.imported_names is not None:
            if node.alias is None:
                for name in node.imported_names:
                    self.define(name, AstSymbol("{}.{}".format(module_name, name), predef=True))
            else:
                self.define(node.alias, AstSymbol("{}.{}".format(module_name, node.imported_names[0]), predef=True))

        else:
            bindings = { key: AstSymbol("{}.{}".format(module_name, key), predef=True) for key in names }
            ns = AstNamespace(module_name, bindings)
            if node.alias is not None:
                self.define(node.alias, ns)
            else:
                self.define(node.module_name, ns)

        if module_name is not None:
            self.imports.add(module_name)
        else:
            self.imports.add(node.module_name)
        return node # AstBody([]) # _cl(AstImport(module_name), node)

    def visit_let(self, node: AstLet):
        prefix, source = self._visit_expr(node.source)
        body = self.visit(node.body)
        if source is node.source and body is node.body:
            return node
        else:
            return _cl(makeBody(prefix, AstLet(node.target, source, body, original_target=node.original_target)), node)

    def visit_list_for(self, node: AstListFor):
        prefix, source = self._visit_expr(node.source)
        expr = self.visit(node.expr)
        target = node.target if node.target in get_info(expr).free_vars else '_'
        if target is node.target and source is node.source and expr is node.expr:
            return node
        else:
            return makeBody(prefix, node.clone(target=target, source=source, expr=expr))

    def visit_observe(self, node: AstObserve):
        d_prefix, dist = self._visit_expr(node.dist)
        v_prefix, value = self._visit_expr(node.value)
        # keep it from being over-zealous
        if len(d_prefix) == 1 and isinstance(d_prefix[0], AstDef) and isinstance(dist, AstSymbol) and \
                        d_prefix[0].name == dist.name and isinstance(d_prefix[0].value, AstCall):
            d_prefix, dist = [], d_prefix[0].value
        if dist is node.dist and value is node.value:
            return node
        else:
            prefix = d_prefix + v_prefix
            return makeBody(prefix, node.clone(dist=dist, value=value))

    def visit_return(self, node: AstReturn):
        prefix, value = self._visit_expr(node.value)
        if value is node.value:
            return node
        else:
            return _cl(makeBody(prefix, AstReturn(value)), node)

    def visit_sample(self, node: AstSample):
        prefix, dist = self._visit_expr(node.dist)
        # keep it from being over zealous
        if len(prefix) == 1 and isinstance(prefix[0], AstDef) and isinstance(dist, AstSymbol) and \
                        prefix[0].name == dist.name and isinstance(prefix[0].value, AstCall):
            prefix, dist = [], prefix[0].value
        if node.size is not None:
            s_prefix, size = self._visit_expr(node.size)
            prefix += s_prefix
        else:
            size = None
        if dist is node.dist and size is node.size:
            return node
        else:
            return makeBody(prefix, node.clone(dist=dist, size=size))

    def visit_slice(self, node: AstSlice):
        prefix, base = self._visit_expr(node.base)
        a_prefix, a = self._visit_expr(node.start)
        b_prefix, b = self._visit_expr(node.stop)
        prefix += a_prefix
        prefix += b_prefix
        if base is node.base and a is node.start and b is node.stop:
            return node
        else:
            return _cl(makeBody(prefix, AstSlice(base, a, b)), node)

    def visit_subscript(self, node: AstSubscript):
        base_prefix, base = self._visit_expr(node.base)
        index_prefix, index = self._visit_expr(node.index)
        if base is node.base and index is node.index:
            return node
        else:
            prefix = base_prefix + index_prefix
            return _cl(makeBody(prefix, makeSubscript(base, index)), node)

    def visit_symbol(self, node: AstSymbol):
        symbol = self.resolve(node.name)
        if symbol is not None:
            return symbol
        return node

    def visit_unary(self, node: AstUnary):
        # when applying an unary operator twice, it usually cancels, so we can get rid of it entirely
        if isinstance(node.item, AstUnary) and node.op == node.item.op:
            if node.op in ('not', '+', '-'):
                return self.visit(node.item.item)
        prefix, item = self._visit_expr(node.item)
        if item is node.item:
            return node
        else:
            prefix.append(AstUnary(node.op, item))
            return _cl(makeBody(prefix), node)

    def visit_vector(self, node: AstVector):
        original_name = getattr(node, 'original_name', None)
        if original_name is not None:
            i = 0
            for item in node.items:
                if getattr(item, 'original_name', None) is None:
                    item.original_name = "{}[{}]".format(original_name, i)
                i += 1
        prefix = []
        items = []
        for item in node.items:
            p, i = self._visit_expr(item)
            prefix += p
            items.append(i)
        return _cl(makeBody(prefix, makeVector(items)), node)

    def visit_while(self, node: AstWhile):
        return self.visit_node(node)
