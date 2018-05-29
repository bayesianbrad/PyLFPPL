#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Feb 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
import math
from ast import copy_location as _cl

from .. import ppl_namespaces
from ..ppl_ast_annotators import *
from ..ppl_branch_scopes import BranchScopeVisitor
from ..transforms import ppl_var_substitutor
from ..types import ppl_types, ppl_type_inference


# Note: Why do we need to protect all mutable variables?
#   During the optimisation, we regularly visit a part of the AST multiple times, and we might even visit a part of
#   the AST even though it might never actually be executed by the program. With LISP-based code, this is usually not
#   a problem. However, with Python, a problem arises with statements such as `x += 1`. If we do not protect the
#   variable `x`, we might accidentally increase the value of `x` more than once (or, in case of an `if`-statement,
#   more than zero times), leading to wrong results.
#   Hence, whenever we enter a new scope, we scan for all variables that are "defined" more than once, and then
#   protect them, making them kind of "read-only".


print("!!!DEPRECATED!!!")


def _all_(coll, p):
    return all([p(item) for item in coll])

def _all_equal(coll, f=None):
    if f is not None:
        coll = [f(item) for item in coll]
    if len(coll) > 0:
        return len([item for item in coll if item != coll[0]]) == 0
    else:
        return True

def _all_instances(coll, cls):
    return all([isinstance(item, cls) for item in coll])



class Simplifier(BranchScopeVisitor):

    def __init__(self, symbols:list):
        super().__init__(symbols)
        self.type_inferencer = ppl_type_inference.TypeInferencer(self)

    def get_type(self, node: AstNode):
        result = self.type_inferencer.visit(node)
        return result

    def parse_args(self, args:list):
        prefix = []
        result = []
        for arg in args:
            arg = self.visit(arg)
            info = get_info(arg)
            if isinstance(arg, AstBody) and not info.has_changed_vars:
                if len(arg) == 0:
                    result.append(AstValue(None))
                elif len(arg) == 1:
                    result.append(arg.items[0])
                else:
                    prefix += arg.items[:-1]
                    result.append(arg.items[-1])
            else:
                result.append(arg)

        return prefix, result

    def visit_expr(self, node:AstNode):
        with self.create_write_lock():
            return self.visit(node)

    def visit_attribute(self, node:AstAttribute):
        base = self.visit(node.base)
        if isinstance(base, AstSymbol):
            ns = self.resolve(base.name)
            if isinstance(ns, AstNamespace):
                return self.visit(ns[node.attr])

        if base is node.base:
            return node
        else:
            return node.clone(base=base)

    def visit_binary(self, node:AstBinary):
        if is_symbol(node.left) and is_symbol(node.right) and \
                        node.op in ('-', '/', '//') and node.left.name == node.right.name:
            return AstValue(0 if node.op == '-' else 1)

        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op
        if is_number(left) and is_number(right):
            return AstValue(node.op_function(left.value, right.value))

        elif op == '+' and is_string(left) and is_string(right):
            return _cl(AstValue(left.value + right.value), node)

        elif op == '+' and isinstance(left, AstValueVector) and isinstance(right, AstValueVector):
            return _cl(AstValueVector(left.items + right.items), node)

        elif op == '*' and (is_string(left) and is_integer(right)) or (is_integer(left) and is_string(right)):
            return _cl(AstValue(left.value * right.value), node)

        elif op == '*' and isinstance(left, AstValueVector) and is_integer(right):
            return _cl(AstValueVector(left.items * right.value), node)

        elif op == '*' and is_integer(left) and isinstance(right, AstValueVector):
            return _cl(AstValueVector(left.value * right.items), node)

        elif is_number(left):
            value = left.value
            if value == 0:
                if op in ('+', '|', '^'):
                    return right
                elif op == '-':
                    return self.visit_expr(_cl(AstUnary('-', right), node))
                elif op in ('*', '/', '//', '%', '&', '<<', '>>', '**'):
                    return left

            elif value == 1:
                if op == '*':
                    return right

            elif value == -1:
                if op == '*':
                    return self.visit_expr(_cl(AstUnary('-', right), node))

            if isinstance(right, AstBinary) and is_number(right.left):
                r_value = right.left.value
                if op == right.op and op in ('+', '-', '*', '&', '|'):
                    return self.visit_expr(_cl(AstBinary(AstValue(node.op_function(value, r_value)),
                                     '+' if op == '-' else op,
                                     right.right), node))

                elif op == right.op and op == '/':
                    return self.visit_expr(_cl(AstBinary(AstValue(value / r_value), '*', right.right), node))

                elif op in ['+', '-'] and right.op in ['+', '-']:
                    return self.visit_expr(_cl(AstBinary(AstValue(node.op_function(value, r_value)), '-', right.right), node))

        elif is_number(right):
            value = right.value
            if value == 0:
                if op in ('+', '-', '|', '^'):
                    return left
                elif op == '**':
                    return AstValue(1)
                elif op == '*':
                    return right

            elif value == 1:
                if op in ('*', '/', '**'):
                    return left

            elif value == -1:
                if op in ('*', '/'):
                    return self.visit_expr(_cl(AstUnary('-', right), node))

            if op == '-':
                op = '+'
                value = -value
                right = AstValue(value)
            elif op == '/' and value != 0:
                op = '*'
                value = 1 / value
                right = AstValue(value)

            if isinstance(left, AstBinary) and is_number(left.right):
                l_value = left.right.value
                if op == left.op and op in ('+', '*', '|', '&'):
                    return self.visit_expr(_cl(AstBinary(left.left, op, AstValue(node.op_function(l_value, value))), node))

                elif op == left.op and op == '-':
                    return self.visit_expr(_cl(AstBinary(left.left, '-', AstValue(l_value + value)), node))

                elif op == left.op and op in ('/', '**'):
                    return self.visit_expr(_cl(AstBinary(left.left, '/', AstValue(l_value * value)), node))

                elif op in ['+', '-'] and left.op in ('+', '-'):
                    return self.visit_expr(_cl(AstBinary(left.left, left.op, AstValue(l_value - value)), node))

            if op in ('<<', '>>') and type(value) is int:
                base = 2 if op == '<<' else 0.5
                return _cl(AstBinary(left, '*', AstValue(base ** value)), node)

        elif is_boolean(left) and is_boolean(right):
            return _cl(AstValue(node.op_function(left.value, right.value)), node)

        elif is_boolean(left):
            if op == 'and':
                return right if left.value else AstValue(False)
            if op == 'or':
                return right if not left.value else AstValue(True)

        elif is_boolean(right):
            if op == 'and':
                return left if right.value else AstValue(False)
            if op == 'or':
                return left if not right.value else AstValue(True)

        if op == '-' and isinstance(right, AstUnary) and right.op == '-':
            return self.visit_expr(_cl(AstBinary(left, '+', right.item), node))

        if left is node.left and right is node.right:
            return node
        else:
            return _cl(AstBinary(left, op, right), node)

    def visit_body(self, node:AstBody):
        items = [self.visit(item) for item in node.items]
        return _cl(makeBody(items), node)

    def visit_call(self, node:AstCall):
        function = self.visit(node.function)
        prefix, args = self.parse_args(node.args)
        if isinstance(function, AstFunction) and all([not get_info(arg).has_changed_vars for arg in args]):
            self.define_all(function.parameters, args, vararg=function.vararg)
            result = self.visit(function.body)
            if function.f_locals is not None:
                result = clean_locals(result, function.f_locals)

            if get_info(result).return_count == 1:
                if isinstance(result, AstReturn):
                    result = result.value
                    result = result if result is not None else AstValue(None)
                    if len(prefix) > 0:
                        result = makeBody(prefix, result)
                    return result

                elif isinstance(result, AstBody) and result.last_is_return:
                    items = prefix + result.items[:-1]
                    result = result.items[-1].value
                    result = result if result is not None else AstValue(None)
                    return makeBody(items, result)

        elif isinstance(function, AstDict):
            if len(args) != 1 or node.has_keyword_args:
                raise TypeError("dict access requires exactly one argument ({} given)".format(node.arg_count))
            return _cl(makeSubscript(function, args[0]), node)

        result = node.clone(function=function, args=args)
        return makeBody(prefix, result)

    def visit_call_abs(self, node: AstCall):
        if node.arg_count == 1 and not node.has_keyword_args:
            arg = self.visit_expr(node.args[0])
            if isinstance(arg, AstValue):
                return _cl(AstValue(abs(arg.value)), node)

        return self.visit_call(node)

    def visit_call_clojure_core_concat(self, node:AstCall):
        import itertools
        if not node.has_keyword_args:
            args = [self.visit(arg) for arg in node.args]
            if all([is_string(item) for item in args]):
                return _cl(AstValue(''.join([item.value for item in args])), node)

            elif all([isinstance(item, AstValueVector) for item in args]):
                return _cl(AstValue(list(itertools.chain([item.value for item in args]))), node)

            elif all([is_vector(item) for item in args]):
                args = [item if isinstance(item, AstVector) else item.to_vector() for item in args]
                return _cl(AstValue(list(itertools.chain([item.value for item in args]))), node)

        return self.visit_call(node)

    def visit_call_clojure_core_conj(self, node:AstCall):
        if not node.has_keyword_args:
            args = [self.visit(arg) for arg in node.args]
            if len(args) > 1 and is_vector(args[0]):
                sequence = args[0]
                for arg in reversed(args[1:]):
                    sequence = sequence.conj(arg)
                return sequence
        return self.visit_call(node)

    def visit_call_clojure_core_cons(self, node:AstCall):
        if not node.has_keyword_args:
            args = [self.visit(arg) for arg in node.args]
            if len(args) > 1 and is_vector(args[-1]):
                sequence = args[-1]
                for arg in reversed(args[:-1]):
                    sequence = sequence.cons(arg)
                return sequence
        return self.visit_call(node)

    def visit_call_len(self, node: AstCall):
        if node.arg_count == 1:
            arg = self.visit_expr(node.args[0])
            if is_vector(arg):
                return AstValue(len(arg))
            arg_type = self.get_type(arg)
            if isinstance(arg_type, ppl_types.SequenceType):
                if arg_type.size is not None:
                    return AstValue(arg_type.size)
        return self.visit_call(node)

    def visit_call_math_sqrt(self, node: AstCall):
        if node.arg_count == 1:
            value = self.visit_expr(node.args[0])
            if isinstance(value, AstValue):
                return _cl(AstValue(math.sqrt(value.value)), node)

        return self.visit_call(node)

    def visit_call_range(self, node:AstCall):
        args = [self.visit(arg) for arg in node.args]
        if 1 <= len(args) <= 2 and all([is_integer(arg) for arg in args]):
            if len(args) == 1:
                result = range(args[0].value)
            else:
                result = range(args[0].value, args[1].value)
            return _cl(AstValueVector(list(result)), node)

        return self.visit_call(node)

    def visit_compare(self, node:AstCompare):
        left = self.visit(node.left)
        right = self.visit(node.right)
        second_right = self.visit(node.second_right)

        if second_right is None:
            if is_unary_neg(left) and is_unary_neg(right):
                left, right = right.item, left.item
            elif is_unary_neg(left) and is_number(right):
                left, right = AstValue(-right.value), left.item
            elif is_number(left) and is_unary_neg(right) :
                right, left = AstValue(-left.value), right.item

            if is_binary_add_sub(left) and is_number(right):
                left = self.visit_expr(AstBinary(left, '-', right))
                right = AstValue(0)
            elif is_binary_add_sub(right) and is_number(left):
                right = self.visit_expr(AstBinary(right, '-', left))
                left = AstValue(0)

        if is_number(left) and is_number(right):
            result = node.op_function(left.value, right.value)
            if second_right is None:
                return _cl(AstValue(result), node)

            elif is_number(second_right):
                result = result and node.op_function_2(right.value, second_right.value)
                return _cl(AstValue(result), node)

        if node.op in ('in', 'not in') and is_vector(right) and second_right is None:
            op = node.op
            for item in right:
                if left == item:
                    return AstValue(True if op == 'in' else False)
            return AstValue(False if op == 'in' else True)

        return _cl(AstCompare(left, node.op, right, node.second_op, second_right), node)

    def visit_def(self, node:AstDef):
        if is_function(node.value):
            self.define(node.name, node.value)
            return node
        else:
            value = self.visit(node.value)

            if is_non_empty_body(value):
                items = value.items[:]
                prefix = []
                while len(items) > 0 and isinstance(items[0], AstDef):
                    prefix.append(items[0])
                    del items[0]
                if len(items) == 0:
                    value = AstValue(None)
                elif len(items) == 1:
                    value = value.items[0]
            else:
                prefix = []

            usage = self.get_usage_count(node.name)
            if usage == 0 or usage == 1 or get_info(value).can_embed:
                self.define(node.name, value)
            if value is not node.value:
                return makeBody(prefix, node.clone(value=value))
            else:
                return node

    def visit_dict(self, node:AstDict):
        items = { key: self.visit(node.items[key]) for key in node.items }
        return node.clone(items=items)

    def visit_for(self, node:AstFor):
        source = self.visit(node.source)
        if is_vector(source):
            result = makeBody([AstLet(node.target, item, node.body) for item in source])
            return self.visit(_cl(result, node))
        else:
            src_type = self.get_type(source)
            if isinstance(src_type, ppl_types.SequenceType) and src_type.size is not None:
                result = makeBody([
                             AstLet(node.target, makeSubscript(source, i), node.body,
                                    original_target=node.original_target) for i in range(src_type.size)
                         ])
                return self.visit(_cl(result, node))

        for name in get_info(node.body).changed_vars:
            self.lock_name(name)
        body = self.visit(node.body)
        return node.clone(source=source, body=body)

    def visit_function(self, node:AstFunction):
        with self.create_lock():
            self.lock_all()
            body = self.visit(node.body)
            if body is not node.body:
                return _cl(AstFunction(node.name, node.parameters, body, vararg=node.vararg,
                                       doc_string=node.doc_string, f_locals=node.f_locals), node)
        return node

    def visit_if(self, node:AstIf):
        # Handle the case of chained conditionals, which (in Lisp) would be written using `cond`.
        cond = node.cond_tuples()
        if len(cond) > 1:
            with self.create_write_lock():
                cond_test = [self.visit(item[0]) for item in cond]
                cond_body = [self.visit(item[1]) for item in cond]

            # No condition needed if all options are equal
            if _all_equal(cond_body):
                return self.visit(makeBody(cond_test, node.if_node))

            # Factor out "observe"
            if _all_instances(cond_body, AstObserve):
                if _all_equal([x.dist for x in cond_body]):
                    return self.visit(
                        AstObserve(cond_body[0].dist,
                                   AstIf.from_cond_tuples(list(zip(cond_test, [x.value for x in cond_body]))))
                    )

                elif _all_equal([x.value for x in cond_body]):
                    return self.visit(
                        AstObserve(AstIf.from_cond_tuples(list(zip(cond_test, [x.dist for x in cond_body]))),
                                   cond_body[0].value)
                    )

            # Factor out a function call
            if _all_instances(cond_body, AstCall) and _all_equal(cond_body, lambda x: x.function_name) and \
                    _all_equal(cond_body, lambda x: x.arg_count) and all([not x.has_keyword_args for x in cond_body]):
                args = [[item.args[i] for item in cond_body] for i in range(cond_body[0].arg_count)]
                new_args = []
                for arg in args:
                    if _all_equal(arg):
                        new_args.append(arg[0])
                    else:
                        new_args.append(AstIf.from_cond_tuples(list(zip(cond_test, arg))))
                return self.visit(AstCall(cond_body[0].function, new_args))

            # Factor out a definition
            if _all_instances(cond_body, AstDef) and _all_equal(cond_body, lambda x: x.name):
                values = [item.value for item in cond_body]
                return self.visit(AstDef(cond_body[0].name, AstIf.from_cond_tuples(list(zip(cond_test, values)))))

            # Check if we can rewrite the condition as a dictionary
            if (all([x.is_equality_const_test if isinstance(x, AstCompare) else False for x in cond_test]) or
                    (all([x.is_equality_const_test if isinstance(x, AstCompare) else False for x in cond_test[:-1]]) and
                     is_boolean_true(cond_test[-1]))) and all([get_info(x).can_embed for x in cond_body]):
                test_vars = []
                test_values = []
                for item in cond_test:
                    if isinstance(item, AstValue):
                        break
                    elif isinstance(item.left, AstValue) and is_symbol(item.right):
                        test_values.append(item.left)
                        test_vars.append(item.right.name)
                    elif is_symbol(item.left) and isinstance(item.right, AstValue):
                        test_values.append(item.right)
                        test_vars.append(item.left.name)
                    else:
                        break
                if len(test_vars) == len(test_values) == len(cond_test) and len(set(test_vars)) == 1:
                    d = AstDict({ a.value:b for a, b in zip(test_values, cond_body) })
                    return self.visit(AstSubscript(d, AstSymbol(test_vars[0])))

                elif len(test_vars) == len(test_values) == len(cond_test)-1 and len(set(test_vars)) == 1 and \
                        is_boolean_true(cond_test[-1]):
                    d = AstDict({ a.value:b for a, b in zip(test_values, cond_body[:-1]) })
                    return self.visit(AstSubscript(d, AstSymbol(test_vars[0]), default=cond_body[-1]))

        # Handle the common case of if/else

        test = self.visit(node.test)

        if is_boolean(test):
            if test.value is True:
                return self.visit(node.if_node)
            elif test.value is False:
                return self.visit(node.else_node)

        with self.create_scope(test):
            if_node = self.visit(node.if_node)
            self.switch_branch()
            else_node = self.visit(node.else_node)

        if is_unary_not(test) and not is_empty(else_node):
            test = test.item
            if_node, else_node = else_node, if_node

        return _cl(AstIf(test, if_node, else_node), node)

    def visit_import(self, node: AstImport):
        module_name, names = ppl_namespaces.namespace_from_module(node.module_name)
        if node.imported_names is not None:
            if node.alias is None:
                for name in node.imported_names:
                    self.define(name, AstSymbol("{}.{}".format(module_name, name), predef=True))
            else:
                self.define(node.alias, AstSymbol("{}.{}".format(module_name, node.imported_names[0]), predef=True))

        else:
            bindings = { key: AstSymbol("{}.{}".format(module_name, key), predef=True) for key in names }
            ns = AstNamespace(module_name, bindings)
            self.define(node.module_name, ns)

        return _cl(AstImport(module_name), node)

    def visit_let(self, node:AstLet):
        if count_variable_usage(node.target, node.body) == 0:
            return self.visit(_cl(makeBody(node.source, node.body), node))

        source = self.visit_expr(node.source)
        src_info = get_info(source)
        if isinstance(source, AstBody) and len(source) > 1:
            result = node.clone(source=source.items[-1])
            result = _cl(makeBody(source.items[:-1], result), node.source)
            return self.visit(result)

        elif src_info.is_independent(get_info(node.body)) and \
                (count_variable_usage(node.target, node.body) == 1 or src_info.can_embed):
            print("CAN EMBED", source, src_info.can_embed, count_variable_usage(node.target, node.body), node.target)
            print(" " * 20, "-->", node.body)
            self.define(node.target, self.visit(node.source))
            return _cl(self.visit(node.body), node)

        return self.visit(makeBody(AstDef(node.target, node.source), node.body))

    def visit_list_for(self, node:AstListFor):
        source = self.visit(node.source)
        if is_vector(source):
            src_len = len(source)
        else:
            src_type = self.get_type(source)
            if isinstance(src_type, ppl_types.SequenceType):
                src_len = src_type.size
            else:
                src_len = None

        if node.test is None:
            if node.target == '_' and src_len is not None:
                if isinstance(node.expr, AstSample) and node.expr.size is None:
                    return self.visit(node.expr.clone(size=AstValue(src_len)))
                else:
                    return self.visit(_cl(makeVector([node.expr for _ in range(src_len)]), node))

            if is_vector(source):
                result = makeVector([AstLet(node.target, item, node.expr,
                                            original_target=node.original_target) for item in source])
                return self.visit(_cl(result, node))

            elif src_len is not None:
                result = makeVector([AstLet(node.target, makeSubscript(source, i), node.expr,
                                             original_target=node.original_target) for i in range(src_len)])
                return self.visit(_cl(result, node))

        for name in get_info(node.expr).changed_vars:
            self.lock_name(name)

        test = self.visit(node.test)
        expr = self.visit(node.expr)
        return _cl(AstListFor(node.target, source, expr, test, original_target=node.original_target), node)

    def visit_observe(self, node:AstObserve):
        dist = self.visit(node.dist)
        value = self.visit(node.value)
        if dist is node.dist and value is node.value:
            return node
        else:
            return _cl(AstObserve(dist, value), node)

    def visit_return(self, node:AstReturn):
        value = self.visit(node.value)
        if isinstance(value, AstBody):
            items = value.items
            ret = self.visit(_cl(AstReturn(items[-1]), node))
            return _cl(makeBody(items[:-1], ret), value)
        elif isinstance(value, AstLet):
            with self.create_lock(value.target):
                ret = self.visit(_cl(AstReturn(value.body), node))
            return _cl(AstLet(value.target, value.source, ret), value)

        if value is not node.value:
            return _cl(AstReturn(value), node)
        else:
            return node

    def visit_sample(self, node:AstSample):
        dist = self.visit(node.dist)
        size = self.visit(node.size)
        if dist is not node.dist or size is not node.size:
            return _cl(AstSample(dist, size=size), node)
        else:
            return node

    def visit_slice(self, node:AstSlice):
        base = self.visit(node.base)
        start = self.visit(node.start)
        stop = self.visit(node.stop)

        if (is_integer(start) or start is None) and (is_integer(stop) or stop is None):
            if isinstance(base, AstValueVector) or isinstance(base, AstVector):
                start = start.value if start is not None else None
                stop = stop.value if stop is not None else None
                if start is not None and stop is not None:
                    return _cl(makeVector(base.items[start:stop]), node)
                elif start is not None:
                    return _cl(makeVector(base.items[start:]), node)
                elif stop is not None:
                    return _cl(makeVector(base.items[:stop]), node)
                else:
                    return _cl(makeVector(base.items), node)

        return _cl(AstSlice(base, start, stop), node)

    def visit_subscript(self, node:AstSubscript):
        base = self.visit(node.base)
        index = self.visit(node.index)
        default = self.visit(node.default)
        if is_integer(index):
            if isinstance(base, AstValueVector):
                if 0 <= index.value < len(base) or default is None:
                    return _cl(AstValue(base.items[index.value]), node)
                else:
                    return _cl(default, node)
            elif isinstance(base, AstVector):
                if 0 <= index.value < len(base) or default is None:
                    result = base.items[index.value]
                    if get_info(result).can_embed:
                        return _cl(result, node)
                else:
                    return _cl(default, node)

        if isinstance(base, AstDict) and isinstance(index, AstValue):
            result = base.items.get(index.value, default)
            if get_info(result).can_embed:
                return result

        return _cl(AstSubscript(base, index, default), node)

    def visit_symbol(self, node:AstSymbol):
        value = self.resolve(node.name)
        if isinstance(value, AstFunction):
            return value
        elif value is not None: #  and get_info(value).can_embed:
            return value
        else:
            return node

    def visit_unary(self, node:AstUnary):
        op = node.op
        if op == '+':
            return self.visit(node.item)

        if op == 'not':
            item = node.item._visit_expr(self)
            if isinstance(item, AstCompare) and item.second_right is None:
                return self.visit(_cl(AstCompare(item.left, item.neg_op, item.right), node))

            if isinstance(item, AstBinary) and item.op in ('and', 'or'):
                return self.visit(_cl(AstBinary(AstUnary('not', item.left), 'and' if item.op == 'or' else 'or',
                                                AstUnary('not', item.right)), node))

            if is_boolean(item):
                return _cl(AstValue(not item.value), node)

        if isinstance(node.item, AstUnary) and op == node.item.op:
            return self.visit(node.item.item)

        item = self.visit(node.item)
        if is_number(item):
            if op == '-':
                return _cl(AstValue(-item.value), node)

        if item is node.item:
            return node
        else:
            return _cl(AstUnary(node.op, item), node)

    def visit_value(self, node:AstValue):
        return node

    def visit_value_vector(self, node:AstValueVector):
        return node

    def visit_vector(self, node:AstVector):
        items = [self.visit(item) for item in node.items]
        if len(items) > 0 and all([isinstance(item, AstSample) and item.size is None for item in items]) and \
                all([item.dist == items[0].dist for item in items]):
            return _cl(AstSample(items[0].dist, size=AstValue(len(items))), node)
        return makeVector(items)

    def visit_while(self, node:AstWhile):
        return node


def clean_locals(ast, f_locals):
    if isinstance(ast, AstBody):
        items = ast.items[:]
        free_vars = [get_info(node).free_vars for node in items]
        i = 0
        while i < len(items):
            if isinstance(items[i], AstDef):
                name = items[i].name
                if name in f_locals and all([name not in fv for fv in free_vars]):
                    del items[i]
                    del free_vars[i]
                    continue
            i += 1

        if len(items) < len(ast.items):
            return _cl(makeBody(items), ast)
        else:
            return ast

    elif isinstance(ast, AstReturn):
        value = clean_locals(ast.value, f_locals)
        if value is not ast.value:
            return _cl(AstReturn(value), ast)
        else:
            return ast

    else:
        return ast


def simplify(ast, symbol_list):
    if type(ast) is list:
        ast = AstBody(ast)

    opt = Simplifier(symbol_list)
    result = opt.visit(ast)

    if isinstance(result, AstBody):
        result = result.items

    # remove definitions that are no longer used
    if type(result) is list:
        free_vars = [get_info(node).free_vars for node in result]
        i = 0
        while i < len(result):
            if isinstance(result[i], AstDef):
                name = result[i].name
                if all([name not in fv for fv in free_vars]):
                    del result[i]
                    del free_vars[i]
                    continue
            i += 1

        i = 0
        bindings = {}
        while i < len(result):
            if isinstance(result[i], AstDef):
                name = result[i].name
                value = result[i].value
                if not isinstance(value, AstFunction):
                    j = i+1
                    usage_count = 0
                    while j < len(result):
                        usage_count += count_variable_usage(name, result[j])
                        j += 1
                    if usage_count <= 1:
                        bindings[name] = value
                        del result[i]
                        continue
            i += 1
        vs = ppl_var_substitutor.VarSubstitutor(bindings)
        for i in range(len(result)):
            result[i] = vs.visit(result[i])

    if type(result) in (list, tuple) and len(result) == 1:
        return result[0]
    elif type(result) in (list, tuple):
        return AstBody(result)
    else:
        return result
