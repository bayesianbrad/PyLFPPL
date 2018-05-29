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


class FunctionInliner(TransformVisitor):

    def __init__(self):
        super().__init__()
        self._let_counter = 0

    def visit_call(self, node: AstCall):
        if isinstance(node.function, AstSymbol):
            function = self.resolve(node.function.name)
        elif isinstance(node.function, AstFunction):
            function = node.function
        else:
            function = None
        if isinstance(function, AstFunction):
            args = [self.visit(arg) for arg in node.args]
            tmp = generate_temp_var()
            params = function.parameters[:]
            if function.vararg is not None:
                params.append(function.vararg)
            args = function.order_arguments(args, node.keywords)
            arguments = []
            for p, a in zip(params, args):
                if p != '_' and not isinstance(a, AstSymbol):
                    arguments.append(AstDef(p + tmp, a))
                elif not isinstance(a, AstSymbol):
                    arguments.append(a)
            with self.create_scope(tmp):
                for p, a in zip(params, args):
                    if p != '_':
                        if isinstance(a, AstSymbol):
                            self.define(p, a)
                        else:
                            self.define(p, AstSymbol(p + tmp))
                result = self.visit(function.body)

            if isinstance(result, AstReturn):
                return makeBody(arguments, result.value)
                # result = result.value
                # for p, a in zip(reversed(params), reversed(args)):
                #     if p != '_' and not isinstance(a, AstSymbol):
                #         result = AstLet(p + tmp, a, result)
                #     elif not isinstance(a, AstSymbol):
                #         result = makeBody(a, result)
                # return result

            elif isinstance(result, AstBody) and result.last_is_return:
                if len(result) > 1:
                    return makeBody(arguments, result.items[:-1], result.items[-1].value)
                else:
                    return makeBody(arguments, result.items[-1].value)

        return super().visit_call(node)

    def visit_def(self, node: AstDef):
        if isinstance(node.value, AstFunction):
            self.define(node.name, node.value, globally=node.global_context)
            return node

        elif not node.global_context:
            tmp = self.scope.name
            if tmp is not None and tmp != '':
                value = self.visit(node.value)
                name = node.name + tmp
                self.define(node.name, AstSymbol(name))
                return node.clone(name=name, value=value)

        return super().visit_def(node)

    def visit_let(self, node: AstLet):
        self._let_counter += 1
        tmp = self.scope.name
        if node.target != '_':
            if tmp is None:
                tmp = '__'
            tmp += 'L{}'.format(self._let_counter)
            source = self.visit(node.source)
            with self.create_scope(tmp):
                self.define(node.target, AstSymbol(node.target + tmp))
                body = self.visit(node.body)
            return AstLet(node.target + tmp, source, body)

        else:
            return super().visit_let(node)

    def visit_symbol(self, node: AstSymbol):
        sym = self.resolve(node.name)
        if isinstance(sym, AstSymbol):
            return sym
        else:
            return node
