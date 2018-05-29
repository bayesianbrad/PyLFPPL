#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 21. Dec 2017, Tobias Kohn
# 06. Feb 2018, Tobias Kohn
#
import math
from . import foppl_objects
from . import foppl_parser
from . import distributions
from . import py_parser
from .foppl_ast import *
from .code_objects import *
from .graphs import *
from . import foppl_dataloader
#from .foppl_transformations import Transformations


class Scope(object):
    """
    The scope is basically a stack of dictionaries, implemented as a simply
    linked list of Scope-classes. Functions and other symbols/values are
    stored in distinct dictionaries, and hence also have distinct namespaces.

    If the value of a symbol is of type AstValue, we store this ast-node as
    well. This is then used by the optimizer.
    """

    def __init__(self, prev=None, *, name:str=None):
        self.prev = prev
        self.symbols = {}
        self.functions = {}
        self.name = name

    def find_function(self, name: str):
        if name in self.functions:
            return self.functions[name]
        elif self.prev:
            return self.prev.find_function(name)
        else:
            return None

    def find_symbol(self, name: str):
        if name in self.symbols:
            return self.symbols[name]
        elif self.prev:
            return self.prev.find_symbol(name)
        else:
            return None

    def add_function(self, name: str, value):
        self.functions[name] = value

    def add_symbol(self, name: str, value):
        self.symbols[name] = value

    @property
    def is_global_scope(self):
        return self.prev is None

    def __repr__(self):
        symbols = ', '.join(['{} -> {}'.format(u, self.symbols[u][1]) for u in self.symbols])
        return "Scope\n\tSymbols: {}\n\tFunctions: {}".format(symbols, repr(self.functions))


class ConditionalScope(object):
    """
    Conditional scope
    """

    def __init__(self, prev=None, condition=None, ancestors=None, line_number=-1):
        self.prev = prev
        self.condition = condition
        self.ancestors = ancestors
        self.truth_value = True
        cond = self.condition
        if isinstance(cond, CodeUnary) and cond.op == 'not':
            cond = cond.item
            self.condition = cond
            self.truth_value = not self.truth_value
        if isinstance(cond, CodeCompare) and cond.is_normalized:
            func = cond.left
            self.cond_node = ConditionNode(condition=self.condition, function=func, ancestors=self.ancestors,
                                           line_number=line_number)
        else:
            self.cond_node = ConditionNode(condition=self.condition, ancestors=self.ancestors, line_number=line_number)

    def invert(self):
        self.truth_value = not self.truth_value

    def get_condition(self):
        return self.cond_node, self.truth_value


class Compiler(Walker):
    """
    The Compiler
    """

    __binary_ops = {
        '+': lambda x, y: x + y,
        '-': lambda x, y: x - y,
        '*': lambda x, y: x * y,
        '/': lambda x, y: x / y,
        '**': lambda x, y: x ** y,
        'and': lambda x, y: x & y,
        'or':  lambda x, y: x | y,
        'xor': lambda x, y: x ^ y,
    }

    __vector_ops = {
        'add': lambda x, y: x + y,
        'sub': lambda x, y: x - y,
        'mul': lambda x, y: x * y,
        'div': lambda x, y: x / y,
    }

    def __init__(self):
        self.scope = Scope()
        self.cond_scope = None
        self.graph = Graph.EMPTY
        self.debug_prints = []

    def begin_scope(self, *, name:str=None):
        self.scope = Scope(prev=self.scope,name=name)

    def end_scope(self):
        if not self.scope.is_global_scope:
            self.scope = self.scope.prev
        else:
            raise RuntimeError('[stack underflow] ending global scope')

    def begin_conditional_scope(self, condition, ancestors, line_number=-1):
        self.cond_scope = ConditionalScope(self.cond_scope, condition, ancestors, line_number)

    def end_conditional_scope(self):
        if self.cond_scope:
            self.cond_scope = self.cond_scope.prev
        else:
            raise RuntimeError('[stack underflow] ending conditional scope')

    def invert_conditional_scope(self):
        if self.cond_scope:
            self.cond_scope.invert()

    def current_conditions(self):
        result = []
        c = self.cond_scope
        while c:
            result.append(c.get_condition())
            c = c.prev
        return result

    def _get_current_scope_name(self):
        result = []
        scope = self.scope
        while scope is not None:
            if scope.name is not None:
                result.append(scope.name)
            scope = scope.prev
        if len(result) > 0:
            return '.'.join(reversed(result)) + '.'
        else:
            return ''

    def define(self, name, value):

        def _set_original_name(vertex, orig_name, is_transformed=False):
            original_name = self._get_current_scope_name() + orig_name
            if is_transformed:
                original_name = '~' + original_name
            if vertex is not None:
                if vertex.original_name is None:
                    vertex.original_name = original_name
                if '_' not in vertex.original_name:
                    vertex.original_name = original_name

        if isinstance(name, AstSymbol):
            name = name.name
        if isinstance(name, foppl_objects.Symbol):
            name = name.name
        if isinstance(value, AstFunction):
            self.scope.add_function(name, value)
        else:
            if isinstance(value, Node):
                graph, expr = value.walk(self)
            else:
                graph, expr = value
            if isinstance(expr, CodeSample):
                v = graph.get_vertex_for_distribution(expr.distribution)
                _set_original_name(v, name)

            elif isinstance(expr, CodeFunctionCall) and expr.is_transform_inverse and \
                isinstance(expr.args[0], CodeSample):
                v = graph.get_vertex_for_distribution(expr.args[0].distribution)
                _set_original_name(v, name, True)

            elif isinstance(expr, CodeVector):
                for i in range(len(expr.items)):
                    item = expr.items[i]
                    if isinstance(item, CodeSample):
                        v = graph.get_vertex_for_distribution(item.distribution)
                        _set_original_name(v, "{}_{}".format(name, i))

                if all([isinstance(item, CodeVector) for item in expr.items]):
                    for i in range(len(expr.items)):
                        vec_items = expr.items[i].items
                        for j in range(len(vec_items)):
                            item = vec_items[j]
                            if isinstance(item, CodeSample):
                                v = graph.get_vertex_for_distribution(item.distribution)
                                _set_original_name(v, "{}_{}_{}".format(name, i, j))

            self.scope.add_symbol(name, (graph, expr))

    def resolve_function(self, name):
        return self.scope.find_function(name)

    def resolve_symbol(self, name):
        return self.scope.find_symbol(name)

    def _merge_graph(self, graph):
        self.graph = self.graph.merge(graph)

    def add_debug_print(self, eval_function):
        if isinstance(eval_function, CodeSample):
            name = eval_function.vertex.display_name
        else:
            name = repr(eval_function)
        self.debug_prints.append((name, eval("lambda state: {}".format(eval_function.to_py()))))

    def apply_function(self, function: AstFunction, args: list):
        """
        Applies a function to a series of arguments by simple substitution/replacement.

        The effect of this method is the same as if the arguments were bound to the parameters by `let`
        and the body of the function was then evaluated. This means, that the method opens a new scope,
        binds all arguments to their respective parameters, and then evaluates the body through walking
        it using the compiler as the walker.

        The major limitation of this approach is that values might actually be evaluated more than once
        and not in the order of the arguments. In other words: this works only if we assume that all
        arguments/values are pure in the functional sense, i.e. without side effects.

        :param function:  The function to be applied, as a `AstFunction`-object.
        :param args:      All arguments as a list of AST-nodes.
        :return:          A tuple (graph, expr).
        """
        assert isinstance(function, AstFunction)
        if len(function.params) != len(args):
            raise SyntaxError("wrong number of arguments for '{}'".format(function.name))

        bindings = []
        for (name, value) in zip(function.params, args):
            if isinstance(name, Symbol):
                name = name.name
            if isinstance(value, AstFunction):
                bindings.append((name, value))
            else:
                if type(value) in [int, bool, str, float]:
                    bindings.append((name, (Graph.EMPTY, AstValue(value))))
                elif type(value) is tuple and len(value) == 2:
                    bindings.append((name, value))
                else:
                    bindings.append((name, value.walk(self)))

        self.begin_scope(name=function.name)
        try:
            for name, value in bindings:
                self.define(name, value)
            result = function.body.walk(self)
        finally:
            self.end_scope()
        return result

    def _make_sequence(self, node: Node):
        if isinstance(node, AstValue) and type(node.value) is list:
            return [(Graph.EMPTY, CodeValue(v)) for v in node.value]
        elif isinstance(node, AstVector):
            return [v.walk(self) for v in node.items]
        else:
            graph, code = node.walk(self)
            if isinstance(code, CodeValue) and type(code.value) is list:
                return [(Graph.EMPTY, CodeValue(v)) for v in code.value]
            elif isinstance(code, CodeVector):
                return [(graph, item) for item in code.items]
            elif isinstance(code, CodeDataSymbol):
                return [(Graph.EMPTY, CodeValue(v)) for v in code.node.data]
            elif isinstance(code.code_type, SequenceType) and code.code_type.size is not None:
                return [(graph, CodeSubscript(code, CodeValue(i))) for i in range(code.code_type.size)]
            else:
                raise TypeError("cannot resolve '{}' to a sequence".format(repr(node)))

    def visit_node(self, node: Node):
        raise NotImplementedError(node)

    def visit_binary(self, node: AstBinary):
        graph_l, code_l = node.left.walk(self)
        graph_r, code_r = node.right.walk(self)
        graph = merge(graph_l, graph_r)

        if isinstance(code_l, CodeValue) and isinstance(code_r, CodeValue) and node.op in self.__binary_ops:
            return graph, CodeValue(self.__binary_ops[node.op](code_l.value, code_r.value))

        elif isinstance(code_l, CodeValue):
            value = code_l.value
            if value == 0:
                if node.op == '+':
                    return graph, code_r
                elif node.op == '-':
                    return AstUnary('-', node.right).walk(self)
                elif node.op in ['*', '/']:
                    return graph, code_l
            elif value == 1:
                if node.op == '*':
                    return graph, code_r

        elif isinstance(code_r, CodeValue):
            value = code_r.value
            if value == 0:
                if node.op in ['+', '-']:
                    return graph, code_l
                elif node.op == '*':
                    return graph, code_r
            elif value == 1:
                if node.op in ['*', '/']:
                    return graph, code_l

        code = CodeBinary(code_l, node.op, code_r)
        return graph, code

    def visit_body(self, node: AstBody):
        graph = Graph.EMPTY
        code = CodeValue(None)
        for item in node.body:
            result = item.walk(self)
            if result:
                g, code = result
                self._merge_graph(g)
                graph = g
        return graph, code

    def visit_call_conj(self, node: AstFunctionCall):
        if len(node.args) >= 2:
            args = [arg.walk(self) for arg in node.args]
            graph = merge(*[g for g, _ in args])
            args = [item for _, item in args]
            seq = args[0]
            items = args[1:]
            if isinstance(seq, CodeValue) and type(seq.value) is list:
                if all([isinstance(item, CodeValue) for item in items]):
                    return graph, CodeValue(seq.value + [item.value for item in items])
                else:
                    return graph, CodeVector([CodeValue(item) for item in seq.value] + items)
            elif isinstance(seq, CodeVector):
                return graph, CodeVector(seq.items + items)
            elif isinstance(seq, CodeDataSymbol):
                values = seq.node.data
                if all([isinstance(item, CodeValue) for item in items]):
                    return graph, CodeValue(values + [item.value for item in items])
                else:
                    return graph, CodeVector([CodeValue(item) for item in values] + items)
        return self.visit_functioncall(node)

    def visit_call_exp(self, node: AstFunctionCall):
        if len(node.args) == 1:
            graph, arg = node.args[0].walk(self)
            if isinstance(arg, CodeValue) and type(arg.value) in [int, float]:
                return graph, CodeValue(math.exp(arg.value))
            else:
                return graph, CodeFunctionCall('math.exp', [arg])
        else:
            raise SyntaxError("'exp' requires exactly one argument")

    def visit_call_drop(self, node: AstFunctionCall):
        args = node.args
        if len(node.args) == 2:
            n_graph, n_code = args[0].walk(self)
            s_graph, s_code = args[1].walk(self)
            graph = merge(n_graph, s_graph)
            if not isinstance(s_code.code_type, SequenceType):
                raise TypeError("second argument to 'drop' must be a sequence")

            if isinstance(n_code, CodeValue) and type(n_code.value) is int:
                n = n_code.value
                if n == 0:
                    return graph, s_code

                elif n >= len(s_code):
                    return graph, CodeValue([])

                elif isinstance(s_code, CodeValue) and type(s_code) is list:
                    return graph, CodeValue(s_code.value[n:])

                elif isinstance(s_code, CodeVector):
                    return graph, makeVector(s_code.items[n:])

                elif isinstance(s_code, CodeDataSymbol):
                    if len(s_code.node.data) - n > 20:
                        node = DataNode(data=s_code.node.data[n:])
                        self._merge_graph(Graph(set(), data={node}))
                        return graph.merge(Graph(set(), data={node})), CodeDataSymbol(node)
                    else:
                        return graph, makeVector(s_code.node.data[n:])

            return graph, CodeSlice(s_code, n_code, None)

        else:
            raise TypeError("'drop' expects exactly two arguments")

    def visit_call_get(self, node: AstFunctionCall):
        args = node.args
        if len(args) == 2:
            seq_graph, seq_expr = args[0].walk(self)
            idx_graph, idx_expr = args[1].walk(self)
            graph = seq_graph.merge(idx_graph)
            if isinstance(idx_expr, CodeValue) and type(idx_expr.value) is int:
                index = idx_expr.value
                if isinstance(seq_expr, CodeValue) and type(seq_expr.value) is list:
                    return graph, CodeValue(seq_expr.value[index])

                elif isinstance(seq_expr, CodeVector):
                    return graph, seq_expr.items[index]

                elif isinstance(seq_expr, CodeDataSymbol) and type(seq_expr.node.data) is list:
                    return graph, CodeValue(seq_expr.node.data[index])

                elif isinstance(seq_expr, CodeSlice) and seq_expr.endIndex is None:
                    index += seq_expr.beginIndex
                    seq = seq_expr.seq
                    if isinstance(seq, CodeValue) and type(seq.value) is list:
                        return graph, CodeValue(seq.value[index])

                    elif isinstance(seq, CodeVector):
                        return graph, seq.items[index]

                    elif isinstance(seq, CodeDataSymbol) and type(seq.node.data) is list:
                        return graph, CodeValue(seq.node.data[index])

                    return graph, CodeSubscript(seq_expr.seq, index)

                else:
                    return graph, CodeSubscript(seq_expr, idx_expr)

            elif isinstance(seq_expr, CodeVector) and isinstance(seq_expr.head, CodeDistribution):
                # We made sure in `visit_vector` that a vector with a distribution contains the same
                # type of distribution and nothing else, i.\,e. all distributions are of type `normal`.
                distr_name = seq_expr.head.name
                dist = distributions.get_distribution_for_name(distr_name)
                arg_count = dist.parameter_count if dist is not None else 0
                args = [makeVector([item.args[k] for item in seq_expr.items]) for k in range(arg_count)]
                args = [makeSubscript(arg, idx_expr) for arg in args]
                return graph, CodeDistribution(distr_name, args)
            else:
                return graph, makeSubscript(seq_expr, idx_expr)

        else:
            raise SyntaxError("'get' expects exactly two arguments")

    def visit_call_interleave(self, node: AstFunctionCall):
        arguments = [arg.walk(self) for arg in node.args]
        if len(arguments) > 0:
            graph = merge(*[g for g, _ in arguments])
            if all([is_vector(item) for item in arguments]):
                args = []
                for _, arg in arguments:
                    if isinstance(arg, CodeValue) and type(arg.value) is list:
                        args.append([CodeValue(v) for v in arg.value])
                    elif isinstance(arg, CodeVector):
                        args.append(arg.items)
                    elif isinstance(arg, CodeDataSymbol):
                        args.append([CodeValue(v) for v in arg.node.data])
                    else:
                        raise TypeError("arguments to 'interleave' must be vectors/lists, not '{}'".format(arg.code_type))
                result = []
                L = min([len(arg) for arg in args])
                for i in range(L):
                    result.append(makeVector([arg[i] for arg in args]))
                return graph, CodeVector(result)
            else:
                return graph, CodeFunctionCall('zip', [item for _, item in arguments])
        else:
            raise TypeError("'interleave' requires at least one argument")

    def visit_call_load(self, node: AstFunctionCall):
        if len(node.args) == 1 and isinstance(node.args[0], AstValue) and type(node.args[0].value is str):
            source = foppl_dataloader.find_path(node.args[0].value)
            data = foppl_dataloader.load_from_source(source) if source is not None else None
            if data is None:
                raise IOError("data-source could not be found: '{}'".format(source))

            node = DataNode(data=data, source=source)
            self._merge_graph(Graph(set(), data={node}))
            result = Graph(set(), data={node}), CodeDataSymbol(node)
            return result
        else:
            raise TypeError("'load' requires s single string-argument")

    def visit_call_map(self, node: AstFunctionCall):
        if len(node.args) < 2:
            raise TypeError("not enough arguments for 'map'")
        function = node.args[0]
        if isinstance(function, AstSymbol):
            f = self.resolve_function(function.name)
            if f is not None: function = f
        if not isinstance(function, AstFunction):
            raise TypeError("first argument to 'map' must be a function, not '{}'".format(repr(function)))

        args = [self._make_sequence(arg) for arg in node.args[1:]]
        if len(args) > 1:
            mangled_args = []
            L = min([len(arg) for arg in args])
            for i in range(L):
                mangled_args.append([arg[i] for arg in args])
            args = mangled_args
        else:
            args = [[arg] for arg in args[0]]

        vec = [self.apply_function(function, arg) for arg in args]
        graph = merge(*[graph for graph, _ in vec])
        if all([isinstance(item, CodeValue) for _, item in vec]):
            result = CodeValue([item.value for _, item in vec])
            return graph, result
        else:
            return graph, CodeVector([item for _, item in vec])

    def visit_call_matrix_functions(self, node: AstFunctionCall):
        if not Options.de_vectorize:
            return self.visit_functioncall(node)

        name = node.function[7:]
        if name in self.__vector_ops and len(node.args) == 2:
            op = self.__vector_ops[name]
            args = [arg.walk(self) for arg in node.args]
            graph = merge(*[g for g, _ in args])
            first, second = args
            first, second = first[1], second[1]
            if isinstance(first.code_type, SequenceType) and isinstance(second.code_type, SequenceType) and \
                    first.code_type.size == second.code_type.size:

                if isinstance(first, CodeValue) and isinstance(second, CodeValue):
                    return graph, CodeValue([op(u, v) for u, v in zip(first.value, second.value)])

                if (isinstance(first, CodeValue) or isinstance(first, CodeVector)) and \
                        (isinstance(second, CodeValue) or isinstance(second, CodeVector)):
                    left = first.value if isinstance(first, CodeValue) else first.items
                    right = second.value if isinstance(second, CodeValue) else second.items
                    return graph, CodeVector([makeBinary(u, name, v) for u, v in zip(left, right)])

            elif isinstance(first.code_type, SequenceType) and isinstance(second.code_type, NumericType):

                if isinstance(first, CodeValue) and isinstance(second, CodeValue):
                    right = second.value
                    return graph, CodeValue([op(u, right) for u in first.value])

                if isinstance(first, CodeValue) or isinstance(first, CodeVector):
                    left = first.value if isinstance(first, CodeValue) else first.items
                    return graph, CodeVector([makeBinary(u, name, second) for u in left])

            elif isinstance(first.code_type, NumericType) and isinstance(second.code_type, SequenceType):

                if isinstance(first, CodeValue) and isinstance(second, CodeValue):
                    left = second.value
                    return graph, CodeValue([op(left, u) for u in second.value])

                if isinstance(second, CodeValue) or isinstance(second, CodeVector):
                    right = second.value if isinstance(second, CodeValue) else second.items
                    return graph, CodeVector([makeBinary(first, name, u) for u in right])

        elif name == 'mmul' and len(node.args) == 2:
            args = [arg.walk(self) for arg in node.args]
            graph = merge(*[g for g, _ in args])
            first, second = args
            first, second = first[1], second[1]
            if isinstance(first, CodeVector):
                left = first.items
            elif isinstance(first, CodeValue):
                left = first.value
            elif isinstance(first, CodeDataSymbol):
                left = first.node.data
            else:
                left = None

            if type(left) is list and is_vector(second):
                result = []
                for item in left:
                    value = CodeValue(0)
                    for i in range(len(item)):
                        v = makeBinary(item[i], '*', second[i])
                        value = makeBinary(value, '+', v)
                    result.append(value)
                return graph, makeVector(result)

        elif name in ['ge', 'gt', 'lt', 'le'] and len(node.args) == 2:
            args = [arg.walk(self) for arg in node.args]
            graph = merge(*[g for g, _ in args])
            first, second = args
            first, second = first[1], second[1]

            if isinstance(first.code_type, SequenceType) and isinstance(second, CodeValue) and \
                            type(second.value) in [int, float]:
                if isinstance(first, CodeValue) and type(first.value) is list:
                    first = [CodeValue(item) for item in first.value]
                elif isinstance(first, CodeVector):
                    first = first.items
                elif first.code_type.size is not None:
                    first = [CodeSubscript(first, CodeValue(i)) for i in range(first.code_type.size)]
                else:
                    first = None
                if first is not None:
                    return graph, makeVector([makeBinary(item, name, second) for item in first])

        return self.visit_functioncall(node)

    def visit_call_print(self, node: AstFunctionCall):
        # This is actually for debugging purposes
        args = [arg.walk(self)[1] for arg in node.args]
        print(', '.join([repr(arg) for arg in args]))
        for arg in args:
            self.add_debug_print(arg)
        return Graph.EMPTY, CodeValue(None)

    def visit_call_range(self, node: AstFunctionCall):
        args = [arg.walk(self) for arg in node.args]
        if len(args) == 1 and args[0][1].code_type == IntegerType:
            graph, arg = args[0]
            if isinstance(arg, CodeValue):
                n = int(arg.value)
                return graph, CodeValue(list(range(n)))
        elif len(args) == 2 and args[0][1].code_type == IntegerType:
            graph_b, arg_b = args[0]
            graph_e, arg_e = args[1]
            graph = merge(graph_b, graph_e)
            if isinstance(arg_b, CodeValue) and isinstance(arg_e, CodeValue):
                b = int(arg_b.value)
                e = int(arg_e.value)
                return graph, CodeValue(list(range(b, e)))
        raise TypeError("'range' expects exactly one integer argument")

    def visit_call_repeat(self, node: AstFunctionCall):
        if len(node.args) != 2:
            raise TypeError("wrong number of arguments: 'repeat' requires exactly two arguments, not {}".format(len(node.args)))
        iter_graph, iter_count = node.args[0].walk(self)
        if isinstance(iter_count, CodeValue) and iter_count.code_type == IntegerType:
            n = iter_count.value
            graph, value = node.args[1].walk(self)
            graph = graph.merge(iter_graph)
            if isinstance(value, CodeValue):
                return graph, CodeValue([value.value] * n)
            else:
                return graph, CodeVector([value] * n)
        else:
            raise TypeError("first argument of 'repeat' must be an integer")

    def visit_call_repeatedly(self, node: AstFunctionCall):
        if len(node.args) != 2:
            raise TypeError("wrong number of arguments: 'repeatedly' requires exactly two arguments, not {}".format(len(node.args)))
        iter_graph, iter_count = node.args[0].walk(self)
        if isinstance(iter_count, CodeValue) and iter_count.code_type == IntegerType:
            n = iter_count.value
            graph, code = AstVector([node.args[1]] * n).walk(self)
            return graph.merge(iter_graph), code
        else:
            raise TypeError("first argument of 'repeatedly' must be an integer")

    def visit_call_rest(self, node: AstFunctionCall):
        args = node.args
        if len(args) == 1:
            graph, expr = args[0].walk(self)
            if isinstance(expr, CodeValue) and type(expr.value) is list:
                return graph, CodeValue(expr.value[1:])

            elif isinstance(expr, CodeVector):
                return graph, CodeVector(expr.items[1:])

            elif isinstance(expr, CodeSlice) and expr.endIndex is None:
                return graph, CodeSlice(expr.seq, expr.beginIndex+1, None)

            else:
                return graph, CodeSlice(expr, 1, None)
        else:
            raise SyntaxError("'rest' expects exactly one argument")

    def visit_call_sqrt(self, node: AstFunctionCall):
        node = AstSqrt(node.args[0])
        return node.walk(self)

    def visit_call_take(self, node: AstFunctionCall):
        args = node.args
        if len(node.args) == 2:
            n_graph, n_code = args[0].walk(self)
            s_graph, s_code = args[1].walk(self)
            graph = merge(n_graph, s_graph)
            if not isinstance(s_code.code_type, SequenceType):
                raise TypeError("second argument to 'take' must be a sequence")

            if isinstance(n_code, CodeValue) and type(n_code.value) is int:
                n = n_code.value
                if n == 0:
                    return graph, CodeValue([])

                elif n >= len(s_code):
                    return graph, s_code

                elif isinstance(s_code, CodeValue) and type(s_code) is list:
                    return graph, CodeValue(s_code.value[:n])

                elif isinstance(s_code, CodeVector):
                    return graph, makeVector(s_code.items[:n])

                elif isinstance(s_code, CodeDataSymbol):
                    if n > 20:
                        node = DataNode(data=s_code.node.data[:n])
                        self._merge_graph(Graph(set(), data={node}))
                        return graph.merge(Graph(set(), data={node})), CodeDataSymbol(node)

                    else:
                        return graph, makeVector(s_code.node.data[:n])

            return graph, CodeSlice(s_code, None, n_code)

        else:
            raise TypeError("'take' expects exactly two arguments")

    def visit_compare(self, node: AstCompare):
        graph_l, code_l = node.left.walk(self)
        graph_r, code_r = node.right.walk(self)
        graph = merge(graph_l, graph_r)
        code = CodeCompare(code_l, node.op, code_r)
        return graph, code

    def visit_def(self, node: AstDef):
        if self.scope.is_global_scope:
            self.define(node.name, node.value)
            return Graph.EMPTY, CodeValue(None)
        else:
            raise SyntaxError("'def' must be on the global level")

    def visit_distribution(self, node: AstDistribution):
        args = self.walk_all(node.args)
        graph = merge(*[g for g, _ in args])
        return graph, CodeDistribution(node.name, [a for _, a in args])

    def visit_expr(self, node: AstExpr):
        return node.value

    def visit_for(self, node: AstFor):
        seq = self._make_sequence(node.sequence)
        result = Graph.EMPTY, CodeValue(None)
        self.begin_scope()
        try:
            for item in seq:
                self.define(node.target, item)
                result = node.body.walk(self)
        finally:
            self.end_scope()
        return result

    def visit_functioncall(self, node: AstFunctionCall):
        # NB: some functions are handled directly by visit_call_XXX-methods!
        func = node.function
        if isinstance(func, AstSymbol):
            func = func.name
        if type(func) is str:
            func_name = func
            func = self.scope.find_function(func)
        else:
            func_name = None

        if isinstance(func, AstFunction):
            return self.apply_function(func, node.args)

        elif func_name:
            args = []
            graph = Graph.EMPTY
            for a in node.args:
                g, e = a.walk(self)
                graph = graph.merge(g)
                args.append(e)

            if func_name in runtime.__all__:
                func_name = 'runtime.' + func_name

            return graph, CodeFunctionCall(func_name, args)

        else:
            raise SyntaxError("'{}' is not a function".format(node.function))

    def visit_if(self, node: AstIf):
        cond_graph, cond = node.cond.walk(self)
        self.begin_conditional_scope(cond, cond_graph.vertices, node.line_number)
        try:
            graph, if_code = node.if_body.walk(self)
            if node.else_body is not None:
                self.invert_conditional_scope()
                else_graph, else_code = node.else_body.walk(self)
                graph = merge(graph, else_graph)
            else:
                else_code = None
        finally:
            self.end_conditional_scope()
        graph = merge(cond_graph, graph)
        return graph, CodeIf(cond, if_code, else_code)

    def visit_let(self, node: AstLet):
        self.begin_scope()
        try:
            for (name, value) in node.bindings:
                self.define(name, value)
            result = node.body.walk(self)
        finally:
            self.end_scope()
        return result

    def visit_loop(self, node: AstLoop):
        if isinstance(node.function, AstSymbol):
            function = self.scope.find_function(node.function.name)
        elif isinstance(node.function, AstFunction):
            function = node.function
        else:
            raise SyntaxError("'loop' requires a function")

        iter_count = node.iter_count
        if type(iter_count) is not int:
            g, n = iter_count.walk(self)
            if isinstance(n, CodeValue) and type(n.value) is int and g.is_empty:
                iter_count = n.value
            else:
                raise TypeError("'loop' requires a constant integer value")
        if iter_count == 0:
            return Graph.EMPTY, CodeValue(None)

        i = 0
        args = [AstExpr(*a.walk(self)) for a in node.args]
        result = node.arg.walk(self)
        while i < iter_count:
            result = self.apply_function(function, [AstValue(i), AstExpr(*result)] + args)
            i += 1
        return result

    def visit_multifor(self, node: AstMultiFor):
        sources = [self._make_sequence(source) for source in node.sources]
        iter_count = min([len(source) for source in sources])
        result = Graph.EMPTY, CodeValue(None)
        self.begin_scope()
        try:
            for i in range(iter_count):
                for j in range(len(node.targets)):
                    self.define(node.targets[j], sources[j][i])
                result = node.body.walk(self)
        finally:
            self.end_scope()
        return result

    def visit_observe(self, node: AstObserve):
        graph, dist = node.distribution.walk(self)
        obs_graph, obs_value = node.value.walk(self)
        if not isinstance(dist, CodeDistribution):
            raise TypeError("'observe' requires a distribution as first parameter, not '{}'".format(dist))
        distribution = dist.distribution
        if distribution.has_transformations:
            t_forward = distribution.tranform_forward
            if t_forward is not None:
                obs_value = CodeFunctionCall(t_forward, [obs_value])
            t_new_dist = distribution.transform_distribution
            if t_new_dist is not None:
                dist = CodeDistribution(t_new_dist, dist.args)
        vertex = Vertex(ancestor_graph=merge(graph, obs_graph), distribution=dist, observation=obs_value,
                        conditions=self.current_conditions(), line_number=node.line_number)
        graph = Graph({vertex}).merge(graph)
        self._merge_graph(graph)
        return Graph.EMPTY, CodeObserve(vertex)

    def visit_sample(self, node: AstSample):
        graph, dist = node.distribution.walk(self)
        if not isinstance(dist, CodeDistribution):
            raise TypeError("'sample' requires a distribution as first parameter, not '{}'".format(dist))
        distribution = dist.distribution
        if distribution.has_transformations:
            t_invert = distribution.transform_invert
            t_new_dist = distribution.transform_distribution
            if t_new_dist is not None:
                dist = CodeDistribution(t_new_dist, dist.args)
        else:
            t_invert = None
        vertex = Vertex(ancestor_graph=graph, distribution=dist, conditions=self.current_conditions(),
                        line_number=node.line_number)
        graph = Graph({vertex}).merge(graph)
        self._merge_graph(graph)
        code = CodeSample(vertex)
        if t_invert is not None and t_invert != "":
            code = CodeFunctionCall(t_invert, [code], is_transform_inverse=True)
        return graph, code

    def visit_sqrt(self, node: AstSqrt):
        graph, code = node.item.walk(self)
        if isinstance(code, CodeValue) and type(code.value) in [int, float]:
            return graph, CodeValue(math.sqrt(code.value))
        else:
            return graph, CodeSqrt(code)

    def visit_symbol(self, node: AstSymbol):
        result = self.resolve_symbol(node.name)
        if result is None:
            if len(node.name) > 1 and node.name.startswith('-'):
                result = self.resolve_symbol(node.name[1:])
                if result is not None:
                    raise NameError("the symbol '{}' cannot be found. Did you mean '(- {})'?".format(
                        node.name, node.name[1:]
                    ))
            raise NameError("symbol '{}' not found".format(node.name))
        return result

    def visit_unary(self, node: AstUnary):
        if isinstance(node.item, AstUnary) and node.op == node.item.op:
            return node.item.item.walk(self)
        elif node.op == '+':
            return node.item.walk(self)
        else:
            graph, code = node.item.walk(self)

            if isinstance(code, CodeUnary) and code.op == node.op:
                return graph, code.item

            elif isinstance(code, CodeValue):
                value = code.value
                if node.op == '-':
                    return graph, CodeValue(-value)
                elif node.op == 'not':
                    return graph, CodeValue(not value)

            return graph, CodeUnary(node.op, code)

    def visit_value(self, node: AstValue):
        value = node.value
        if type(value) is list and (len(value) > 3 or any([type(item) is list for item in value])):
            value = DataNode(data=value)
            self._merge_graph(Graph(set(), data={value}))
            return Graph(set(), data={value}), CodeDataSymbol(value)
        else:
            return Graph.EMPTY, CodeValue(node.value)

    def visit_vector(self, node: AstVector):
        items = self.walk_all(node.items)
        if len(items) == 0:
            return Graph.EMPTY, CodeValue([])
        graph = merge(*[g for g, _ in items])
        items = [i for _, i in items]
        code = CodeVector(items)
        if all([isinstance(item, CodeDistribution) for item in items]):
            names = set([item.name for item in items])
            if len(names) > 1:
                raise TypeError("vector/list cannot contain distributions of different types: '{}'".format(names))
        elif any([isinstance(item, CodeDistribution) for item in items]):
            raise TypeError("vector/list cannot contain distributions of different types: '{}'".format(items))
        return graph, code


def _detect_language(source:str):
    i = 0
    while i < len(source) and source[i] <= ' ': i += 1
    if i < len(source):
        c = source[i]
        if c in [';', '(']:
            return 'clj'
        elif c in ['#'] or 'A' <= c <= 'Z' or 'a' <= c <= 'z':
            return 'py'
    return None


def compile(source):
    if type(source) is str:
        lang = _detect_language(source)
        if lang == 'py':
            ast = py_parser.parse(source)
        elif lang == 'clj':
            ast = foppl_parser.parse(source)
        else:
            ast = None

    elif isinstance(source, Node):
        ast = source

    else:
        ast = None

    if ast:
        compiler = Compiler()
        graph, code = compiler.walk(ast)
        graph = graph.merge(compiler.graph)
        graph.debug_prints = compiler.debug_prints
        return graph, code
    else:
        raise RuntimeError("cannot parse '{}'".format(source))
