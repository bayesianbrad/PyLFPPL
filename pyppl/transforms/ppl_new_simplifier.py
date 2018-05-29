#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Feb 2018, Tobias Kohn
# 23. Mar 2018, Tobias Kohn
#
from ast import copy_location as _cl
from ..ppl_ast_annotators import *
from ..aux.ppl_transform_visitor import TransformVisitor
from ..types import ppl_types, ppl_type_inference


class Simplifier(TransformVisitor):

    def __init__(self):
        super().__init__()
        self.type_inferencer = ppl_type_inference.TypeInferencer(self)
        self.bindings = {}

    def get_type(self, node: AstNode):
        result = self.type_inferencer.visit(node)
        return result

    def define_name(self, name: str, value):
        if name not in ('', '_'):
            self.bindings[name] = value

    def resolve_name(self, name: str):
        return self.bindings.get(name, None)


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
                    return self.visit(_cl(AstUnary('-', right), node))
                elif op in ('*', '/', '//', '%', '&', '<<', '>>', '**'):
                    return left

            elif value == 1:
                if op == '*':
                    return right

            elif value == -1:
                if op == '*':
                    return self.visit(_cl(AstUnary('-', right), node))

            if isinstance(right, AstBinary) and is_number(right.left):
                r_value = right.left.value
                if op == right.op and op in ('+', '-', '*', '&', '|'):
                    return self.visit(_cl(AstBinary(AstValue(node.op_function(value, r_value)),
                                     '+' if op == '-' else op,
                                     right.right), node))

                elif op == right.op and op == '/':
                    return self.visit(_cl(AstBinary(AstValue(value / r_value), '*', right.right), node))

                elif op in ['+', '-'] and right.op in ['+', '-']:
                    return self.visit(_cl(AstBinary(AstValue(node.op_function(value, r_value)), '-', right.right), node))

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
                    return self.visit(_cl(AstUnary('-', right), node))

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
                    return self.visit(_cl(AstBinary(left.left, op, AstValue(node.op_function(l_value, value))), node))

                elif op == left.op and op == '-':
                    return self.visit(_cl(AstBinary(left.left, '-', AstValue(l_value + value)), node))

                elif op == left.op and op in ('/', '**'):
                    return self.visit(_cl(AstBinary(left.left, '/', AstValue(l_value * value)), node))

                elif op in ['+', '-'] and left.op in ('+', '-'):
                    return self.visit(_cl(AstBinary(left.left, left.op, AstValue(l_value - value)), node))

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
            return self.visit(_cl(AstBinary(left, '+', right.item), node))

        if left is node.left and right is node.right:
            return node
        else:
            return _cl(AstBinary(left, op, right), node)

    def visit_call_clojure_core_conj(self, node: AstCall):
        args = [self.visit(arg) for arg in node.args]
        if is_vector(args[0]):
            result = args[0]
            for a in args[1:]:
                result = result.conj(a)
            return result
        else:
            return node.clone(args=args)

    def visit_call_len(self, node: AstCall):
        if node.arg_count == 1:
            arg = self.visit(node.args[0])
            if is_vector(arg):
                return AstValue(len(arg))
            arg_type = self.get_type(arg)
            if isinstance(arg_type, ppl_types.SequenceType):
                if arg_type.size is not None:
                    return AstValue(arg_type.size)
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
                left = self.visit(AstBinary(left, '-', right))
                right = AstValue(0)
            elif is_binary_add_sub(right) and is_number(left):
                right = self.visit(AstBinary(right, '-', left))
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

    def visit_def(self, node: AstDef):
        value = self.visit(node.value)
        if isinstance(value, AstSample):
            return node.clone(value=value)
        self.define_name(node.name, value)
        return AstBody([])

    def visit_for(self, node: AstFor):
        source = self.visit(node.source)
        if is_vector(source):
            items = []
            for item in source:
                items.append(AstDef(node.target, item))
                items.append(node.body)
            return self.visit(makeBody(items))
        else:
            src_type = self.get_type(source)
            if isinstance(src_type, ppl_types.SequenceType) and src_type.size is not None:
                items = []
                for i in range(src_type.size):
                    items.append(AstDef(node.target, makeSubscript(source, i)))
                    items.append(node.body)
                return self.visit(makeBody(items))

        raise RuntimeError("cannot unroll the for-loop [line {}]".format(getattr(node, 'lineno', '?')))

    def visit_if(self, node: AstIf):
        test = self.visit(node.test)
        if isinstance(test, AstValue):
            if test.value is True:
                return self.visit(node.if_node)
            if test.value is False or test.value is None:
                return self.visit(node.else_node)

        if_node = self.visit(node.if_node)
        else_node = self.visit(node.else_node)
        if is_empty(if_node) and is_empty(else_node):
            return test
        return node.clone(test=test, if_node=if_node, else_node=else_node)

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
                items = []
                for item in source:
                    items.append(AstDef(node.target, item))
                    items.append(node.expr)
                return self.visit(makeVector(items))

            elif src_len is not None:
                items = []
                for i in range(src_len):
                    items.append(AstDef(node.target, makeSubscript(source, i)))
                    items.append(node.expr)
                return self.visit(makeVector(items))

        raise RuntimeError("cannot unroll the for-loop [line {}]".format(getattr(node, 'lineno', '?')))

    def visit_subscript(self, node: AstSubscript):
        base = self.visit(node.base)
        index = self.visit(node.index)
        if is_vector(base) and is_integer(index):
            return base[index.value]
        else:
            return node.clone(base=base, index=index)

    def visit_symbol(self, node: AstSymbol):
        value = self.resolve_name(node.name)
        if value is not None:
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
            return node.clone(item=item)

    def visit_vector(self, node:AstVector):
        items = [self.visit(item) for item in node.items]
        if len(items) > 0 and all([isinstance(item, AstSample) and item.size is None for item in items]) and \
                all([item.dist == items[0].dist for item in items]):
            result = _cl(AstSample(items[0].dist, size=AstValue(len(items))), node)
            original_name = getattr(node, 'original_name', None)
            if original_name is not None:
                result.original_name = original_name
            return result
        return makeVector(items)
