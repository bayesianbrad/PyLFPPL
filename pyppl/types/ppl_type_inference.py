#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 19. Feb 2018, Tobias Kohn
# 22. Mar 2018, Tobias Kohn
#
from ..ppl_ast import *
from .ppl_types import *

class TypeInferencer(Visitor):

    __visit_children_first__ = True

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def define(self, name:str, value):
        if name is None or name == '_':
            return
        if self.parent is not None and value is not None:
            result = self.parent.resolve(name)
            if hasattr(result, 'set_type'):
                result.set_type(value)

    def resolve(self, name:str):
        if self.parent is not None:
            result = self.parent.resolve(name)
            if isinstance(result, Type):
                return result
            elif isinstance(result, AstNode):
                return self.visit(result)
        return None

    def get_value_of(self, node: AstNode):
        if isinstance(node, AstValue):
            return node.value
        elif is_call(node, 'len') and node.arg_count == 1:
            result = self.visit(node.args[0])
            if isinstance(result, SequenceType):
                return result.size
        return None


    def visit_binary(self, node: AstBinary):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return node.op_function(left, right)

    def visit_body(self, node:AstBody):
        if node.is_empty:
            return NullType
        else:
            return node.items[-1].get_type()

    def visit_call(self, node: AstCall):
        return AnyType

    def visit_call_len(self, _):
        return Integer

    def visit_call_range(self, node: AstCall):
        if node.arg_count == 2:
            a = self.get_value_of(node.args[0])
            b = self.get_value_of(node.args[1])
            if a is not None and b is not None:
                return List[Integer][b-a]
        elif node.arg_count == 1:
            a = self.get_value_of(node.args[0])
            if a is not None:
                return List[Integer][a]
        return List[Integer]

    def visit_call_torch_function(self, node: AstCall):
        name = node.function_name
        args = [self.visit(arg) for arg in node.args]
        f_name = name[6:] if name.startswith('torch.') else name
        if name.startswith('torch.cuda.'):
            f_name = f_name[5:]
        if node.arg_count == 1:
            if f_name in ('from_numpy',):
                return makeTensor(args[0])
            elif f_name in ('ones', 'zeros'):
                return Tensor[AnyType, self.get_value_of(args[0])]
            elif f_name in ('ones_like', 'zeros_like', 'empty_like'):
                return args[0]
            elif f_name in ('arange',):
                return Tensor[Integer, self.get_value_of(args[0])]
            elif f_name in ('tensor', 'Tensor'):
                return makeTensor(args[0])
            elif f_name in ('FloatTensor', 'IntTensor', 'DoubleTensor', 'HalfTensor',
                            'ByteTensor', 'ShortTensor', 'LongTensor'):
                return makeTensor(args[0], f_name)
            elif f_name in ('abs', 'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'erf', 'exp', 'expm1', 'floor',
                            'frac', 'log', 'log1p', 'neg', 'reciprocal', 'round', 'rsqrt', 'sigmoid', 'sign',
                            'sin', 'sinh', 'sqrt', 'tan', 'tanh', 'trunc'):
                return args[0]
            elif f_name in ('diag',):
                if isinstance(args[0], SequenceType):
                    return Tensor[makeTensor(args[0]), args[0].size]
        if node.arg_count > 0:
            if f_name in ('eye',):
                d1 = self.get_value_of(args[0])
                d2 = self.get_value_of(args[1]) if node.arg_count == 2 else d1
                return Tensor[Tensor[Float, d2], d1]
            elif f_name in ('arange', 'range'):
                pos = node.get_position_of_arg('step', 2)
                start = self.get_value_of(args[0])
                stop = self.get_value_of(args[1])
                if start is not None and stop is not None:
                    count = stop - start
                    if node.arg_count > pos:
                        steps = self.get_value_of(args[pos])
                        if steps is not None and steps > 0:
                            return Tensor[Integer, count / steps]
                        else:
                            return Tensor[Integer]
                    else:
                        return Tensor[Integer, count]
                else:
                    return Tensor
            elif f_name in ('linspace', 'logspace'):
                pos = node.get_position_of_arg('steps', 2)
                if node.arg_count > pos:
                    return Tensor[self.get_value_of(args[pos])]
                else:
                    return Tensor[100]
            elif f_name in ('eq', 'ge', 'gt', 'le', 'lt', 'ne',
                            'add', 'atan2', 'clamp', 'div', 'fmod', 'lerp', 'mul', 'pow', 'remainder'):
                return args[0]
            elif f_name in ('equal', 'isnan'):
                return Boolean
        return Tensor

    def visit_compare(self, _):
        return Boolean

    def visit_def(self, node: AstDef):
        result = self.visit(node.value)
        self.define(node.name, result)
        return result

    def visit_dict(self, node: AstDict):
        base = union(*[self.visit(item) for item in node.items.values()])
        return Dict[base][len(node.items)]

    def visit_for(self, node: AstFor):
        source = self.visit(node.source)
        if isinstance(source, SequenceType):
            self.define(node.target, source.item)
            return self.visit(node.body)
        else:
            return AnyType

    def visit_function(self, node: AstFunction):
        return Function

    def visit_if(self, node: AstIf):
        return union(node.if_node.get_type(), node.else_node.get_type())

    def visit_let(self, node: AstLet):
        self.define(node.target, self.visit(node.source))
        return node.body.get_type()

    def visit_list_for(self, node: AstListFor):
        source = self.visit(node.source)
        if isinstance(source, SequenceType):
            self.define(node.target, source.item)
            result = self.visit(node.expr)
            return List[result][source.size]
        else:
            return AnyType

    def visit_multi_slice(self, node: AstMultiSlice):
        base = self.visit(node.base)
        if base in Tensor:
            return Tensor
        elif base is Array:
            return Array
        else:
            return AnyType

    def visit_sample(self, node: AstSample):
        return Numeric

    def visit_slice(self, node: AstSlice):
        base = self.visit(node.base)
        if isinstance(base, SequenceType):
            return base.slice(node.start_as_int, node.stop_as_int)
        else:
            return AnyType

    def visit_subscript(self, node: AstSubscript):
        base = self.visit(node.base)
        if isinstance(base, SequenceType):
            return base.item_type
        else:
            return AnyType

    def visit_symbol(self, node: AstSymbol):
        result = self.resolve(node.name)
        return result if result is not None else AnyType

    def visit_unary(self, node: AstUnary):
        if node.op == 'not':
            return Boolean
        else:
            return self.visit(node.item)

    def visit_value(self, node: AstValue):
        return from_python(node.value)

    def visit_value_vector(self, node: AstValueVector):
        return from_python(node.items)

    def visit_vector(self, node: AstVector):
        base_type = union(*[self.visit(item) for item in node.items])
        return List[base_type][len(node.items)]
