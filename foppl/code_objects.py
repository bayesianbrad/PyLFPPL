#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 16. Jan 2018, Tobias Kohn
# 06. Feb 2018, Tobias Kohn
#
from . import Config
from .graphs import *
from .code_types import *

##############################################################################

def is_vector(item):
    return isinstance(item, CodeVector) or (isinstance(item, CodeValue) and type(item.value) is list) or \
           isinstance(item, CodeDataSymbol)


##############################################################################

class CodeObject(object):

    code_type = AnyType()

    is_vector_data = False

    def to_py(self, state:dict=None) -> str:
        return repr(self)

##############################################################################

class CodeBinary(CodeObject):

    def __init__(self, left: CodeObject, op: str, right: CodeObject):
        self.left = left
        self.op = op
        self.right = right
        self.code_type = apply_binary(left.code_type, op, right.code_type)

    def __repr__(self):
        return "({}{}{})".format(repr(self.left), self.op, repr(self.right))

    def to_py(self, state:dict=None):
        return "({}{}{})".format(self.left.to_py(state), self.op, self.right.to_py(state))


class CodeCompare(CodeObject):

    def __init__(self, left: CodeObject, op: str, right: CodeObject):
        self.left = left
        self.right = right
        self.op = op
        self.code_type = BooleanType()

    @property
    def is_normalized(self):
        return self.op == '>=' and repr(self.right) == '0'

    def __repr__(self):
        op = "==" if self.op == "=" else self.op
        return "({}{}{})".format(repr(self.left), op, repr(self.right))

    def to_py(self, state:dict=None):
        op = "==" if self.op == "=" else self.op
        return "({}{}{})".format(self.left.to_py(state), op, self.right.to_py(state))


class CodeDataSymbol(CodeObject):

    def __init__(self, node):
        self.node = node
        self.name = node.name
        self.code_type = get_code_type_for_value(node.data)
        self.is_vector_data = True

    def __len__(self):
        return len(self.node.data)

    def __getitem__(self, item):
        return CodeValue(self.node.data[item])

    def __repr__(self):
        return self.name

    def to_py(self, state:dict=None):
        if state is not None and self.name in state:
            return repr(state[self.name])
        else:
            return "state['{}']".format(self.name)


class CodeDistribution(CodeObject):

    def __init__(self, name, args):
        from . import distributions
        self.name = name
        self.args = args
        self.distribution = distributions.get_distribution_for_name(name)
        self.dist_type = str(self.distribution.distribution_type)
        self.code_type = DistributionType(self.distribution, [a.code_type for a in args])

    def __repr__(self):
        args = [repr(a) for a in self.args]
        return self.distribution._generate_code_for_node(args)

    def to_py(self, state:dict=None):
        args = [a.to_py(state) for a in self.args]
        return self.distribution._generate_code_for_node(args)

    def to_py_log_pdf(self, *, state:dict=None, value:str):
        args = [a.to_py(state) for a in self.args]
        return self.distribution.generate_code_log_pdf(args, value)

    def to_py_sample(self, *, state:dict=None):
        args = [a.to_py(state) for a in self.args]
        return self.distribution.generate_code_sample(args)

    def get_sample_size(self):
        return self.distribution.get_sample_size(self.args)

    def get_support_size(self):
        return self.distribution.get_support_size(self.args)


class CodeFunctionCall(CodeObject):

    def __init__(self, name, args, is_transform_inverse:bool=False):
        if type(args) is not list:
            args = [args]
        self.name = name
        self.args = args
        self.is_transform_inverse = is_transform_inverse
        if self.is_transform_inverse and len(args) >= 1:
            self.code_type = args[0].code_type
        else:
            self.code_type = self._get_code_type()

    def __repr__(self):
        return "{}({})".format(self.name, ', '.join([repr(a) for a in self.args]))

    def _get_code_type(self):
        name = "_type_" + self.name.lower().replace('/', '_').replace('.', '_')
        method = getattr(self, name, None)
        if method is not None:
            return method()
        else:
            return AnyType()

    def to_py(self, state:dict=None):
        name = self.name.replace('/', '.')
        result = "{}({})".format(name, ', '.join([a.to_py(state) for a in self.args]))
        if name == 'zip':
            return "list({})".format(result)
        else:
            return result

    def _type_elementwise_ops(self):
        if len(self.args) == 0:
            return AnyType()
        elif len(self.args) == 1:
            return self.args[0].code_type
        elif len(self.args) == 2:
            left = self.args[0].code_type
            right = self.args[1].code_type
            if isinstance(left, SequenceType) and isinstance(right, NumericType):
                return left
            if isinstance(left, NumericType) and isinstance(right, SequenceType):
                return right
            if left == right:
                return left

        if all([is_vector(arg) for arg in self.args]):
            return union(*[arg.code_type for arg in self.args])

        return AnyType()

    def _type_elementwise_unary(self):
        if len(self.args) == 1:
            arg = self.args[0].code_type
            if isinstance(arg, SequenceType):
                return ListType(FloatType, arg.size)
            else:
                return arg
        else:
            raise TypeError("too many arguments for '{}'".format(self.name))

    def _type_elementwise_compare(self):
        return self._type_elementwise_ops()

    def _type_matrix_add(self):
        return self._type_elementwise_ops()

    def _type_matrix_sub(self):
        return self._type_elementwise_ops()
    
    def _type_matrix_mul(self):
        return self._type_elementwise_ops()

    def _type_matrix_div(self):
        return self._type_elementwise_ops()

    def _type_matrix_exp(self):
        return self._type_elementwise_unary()

    def _type_matrix_log(self):
        return self._type_elementwise_unary()

    def _type_matrix_ge(self):
        return self._type_elementwise_compare()

    def _type_matrix_mmul(self):
        is_tuple = lambda t: type(t) is tuple and len(t) == 2

        if len(self.args) == 2:
            d0, d1 = [arg.code_type.dimension() for arg in self.args]
            if is_tuple(d0) and is_tuple(d1):
                if d0[1] == d1[0] or d0[1] is None or d1[0] is None:
                    return ListType(ListType(FloatType(), d1[0]), d0[0])

            elif is_tuple(d0) and type(d1) is int:
                if d0[1] == d1 or d0[1] is None or d1 is None:
                    return ListType(FloatType(), d0[0])

            elif type(d0) is int and type(d1) is int:
                return FloatType()

            elif type(d0) is tuple and d1 is None and isinstance(self.args[1].code_type, SequenceType) and \
                    isinstance(self.args[1].code_type.item_type, NumericType):
                return ListType(FloatType(), d0[0])

        return AnyType()

    def _type_zip(self):
        if len(self.args) > 0 and all([isinstance(arg.code_type, SequenceType) for arg in self.args]):
            item_type = self.args[0].code_type.item_type
            size = self.args[0].code_type.size
            for arg in self.args[1:]:
                size = min(size, arg.code_type.size) if size is not None and arg.code_type.size is not None else None
                item_type = item_type.union(arg.code_type.item_type)
            return ListType(ListType(item_type, len(self.args)), size)
        else:
            return AnyType()


class CodeIf(CodeObject):

    def __init__(self, cond:CodeObject, if_expr:CodeObject, else_expr:CodeObject=None):
        self.cond = cond
        self.if_expr = if_expr
        self.else_expr = else_expr
        if not isinstance(cond.code_type, BooleanType):
            raise TypeError("'if'-condition must be of type 'boolean'")
        if else_expr:
            self.code_type = if_expr.code_type.union(else_expr.code_type)
        else:
            self.code_type = if_expr.code_type

    def __repr__(self):
        else_expr = repr(self.else_expr) if self.else_expr is not None else "None"
        return "({} if {} else {})".format(repr(self.if_expr), repr(self.cond), else_expr)

    def to_py(self, state:dict=None):
        else_expr = self.else_expr.to_py(state) if self.else_expr is not None else "None"
        result = "({} if {}{} else {})".format(
            self.if_expr.to_py(state), self.cond.to_py(state), Config.conditional_suffix, else_expr
        )
        return result


class CodeObserve(CodeObject):

    def __init__(self, vertex):
        self.vertex = vertex
        self.distribution = vertex.co_distribution
        self.value = vertex.observation
        self.code_type = self.distribution.code_type.result_type().union(self.value.code_type)

    def __repr__(self):
        return self.vertex.name

    def to_py(self, state:dict=None):
        name = self.vertex.name
        if state is not None and name in state:
            return repr(state[name])
        else:
            return "state['{}']".format(name)


class CodeSample(CodeObject):

    def __init__(self, vertex):
        self.vertex = vertex
        self.distribution = vertex.co_distribution
        self.code_type = self.distribution.code_type.result_type()

    def __repr__(self):
        return self.vertex.name

    def to_py(self, state:dict=None):
        name = self.vertex.name
        if state is not None and name in state:
            return repr(state[name])
        else:
            return "state['{}']".format(name)


class CodeSlice(CodeObject):

    def __init__(self, seq: CodeObject, beginIndex, endIndex):
        self.seq = seq
        self.beginIndex = beginIndex
        self.endIndex = endIndex
        if isinstance(seq.code_type, SequenceType):
            self.code_type = seq.code_type
        else:
            raise TypeError("'{}' is not a sequence".format(repr(seq)))

    def __repr(self, seq_repr):
        if self.beginIndex is None:
            beginIndex = ''
        elif type(self.beginIndex) in [int, float]:
            beginIndex = repr(int(self.beginIndex))
        elif isinstance(self.beginIndex, CodeObject):
            beginIndex = repr(self.beginIndex)
        else:
            raise TypeError("invalid index: '{}'".format(self.beginIndex))

        if self.endIndex is None:
            endIndex = ''
        elif type(self.endIndex) in [int, float]:
            endIndex = repr(int(self.endIndex))
        elif isinstance(self.endIndex, CodeObject):
            endIndex = repr(self.endIndex)
        else:
            raise TypeError("invalid index: '{}'".format(self.endIndex))

        return "{}[{}:{}]".format(repr(self.seq), beginIndex, endIndex)

    def to_py(self, state:dict=None):
        if self.beginIndex is None:
            beginIndex = ''
        elif type(self.beginIndex) in [int, float]:
            beginIndex = repr(int(self.beginIndex))
        elif isinstance(self.beginIndex, CodeObject):
            beginIndex = self.beginIndex.to_py(state)
        else:
            raise TypeError("invalid index: '{}'".format(self.beginIndex))

        if self.endIndex is None:
            endIndex = ''
        elif type(self.endIndex) in [int, float]:
            endIndex = repr(int(self.endIndex))
        elif isinstance(self.endIndex, CodeObject):
            endIndex = self.endIndex.to_py(state)
        else:
            raise TypeError("invalid index: '{}'".format(self.endIndex))

        return "{}[{}:{}]".format(self.seq.to_py(state), beginIndex, endIndex)


class CodeSqrt(CodeObject):

    def __init__(self, item: CodeObject):
        self.item = item
        self.code_type = FloatType()

    def __repr__(self):
        return "math.sqrt({})".format(repr(self.item))

    def to_py(self, state:dict=None):
        return "math.sqrt({})".format(self.item.to_py(state))


class CodeSubscript(CodeObject):

    def __init__(self, seq: CodeObject, index):
        self.seq = seq
        self.index = index
        if isinstance(seq.code_type, SequenceType):
            self.code_type = seq.code_type.item_type
        else:
            raise TypeError("'{}' is not a sequence".format(repr(seq)))

    def __repr__(self):
        if type(self.index) in [int, float]:
            index = repr(int(self.index))
        elif isinstance(self.index, CodeObject):
            index = repr(self.index)
        else:
            raise TypeError("invalid index: '{}'".format(self.index))
        return "{}[{}]".format(repr(self.seq), index)

    def to_py(self, state:dict=None):
        if type(self.index) in [int, float]:
            index = repr(int(self.index))
        elif isinstance(self.index, CodeValue) and self.index.value in [int, float]:
            index = repr(int(self.index.value))
        elif isinstance(self.index, CodeObject):
            if state is None:
                index = "runtime.index({})".format(self.index.to_py(state))
            else:
                index = self.index.to_py(state)
        else:
            raise TypeError("invalid index: '{}'".format(self.index))
        return "{}[{}]".format(self.seq.to_py(state), index)


class CodeSymbol(CodeObject):

    def __init__(self, name: str, code_type: AnyType):
        self.name = name
        self.code_type = code_type

    def __repr__(self):
        return self.name

    def to_py(self, state:dict=None):
        if state is not None and self.name in state:
            return repr(state[self.name])
        else:
            return "state['{}']".format(self.name)


class CodeUnary(CodeObject):

    def __init__(self, op: str, item: CodeObject):
        self.op = op
        self.item = item
        self.code_type = item.code_type

    def __repr__(self):
        op = self.op
        op = op + ' ' if len(op) > 1 else op
        return "{}{}".format(op, repr(self.item))

    def to_py(self, state:dict=None):
        op = self.op
        op = op + ' ' if len(op) > 1 else op
        return "{}{}".format(op, self.item.to_py(state))


class CodeValue(CodeObject):

    def __init__(self, value):
        self.value = value
        self.code_type = get_code_type_for_value(value)
        self.is_vector_data = type(value) is list

    def __len__(self):
        if type(self.value) is list:
            return len(self.value)
        else:
            return 0

    def __getitem__(self, item):
        return CodeValue(self.value[item])

    def dimension(self):
        if type(self.value) is list:
            pass
        else:
            return ()

    def __repr__(self):
        return repr(self.value)


class CodeVector(CodeObject):

    def __init__(self, items):
        self.items = items
        self.code_type = ListType.fromList([i.code_type for i in items])
        self.is_vector_data = True

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def __repr__(self):
        return "[{}]".format(', '.join([repr(i) for i in self.items]))

    @property
    def is_empty(self):
        return len(self.items) == 0

    @property
    def non_empty(self):
        return len(self.items) > 0

    @property
    def head(self):
        return self.items[0] if len(self.items) > 0 else None

    def to_py(self, state:dict=None):
        return "[{}]".format(', '.join([i.to_py(state) for i in self.items]))


#################################################################################################33

_binary_ops = {
    '+': lambda x, y: x + y,
    '-': lambda x, y: x - y,
    '*': lambda x, y: x * y,
    '/': lambda x, y: x / y,
    '**': lambda x, y: x ** y,
    'and': lambda x, y: x & y,
    'or': lambda x, y: x | y,
    'xor': lambda x, y: x ^ y,
}


def makeBinary(left, op: str, right):
    if op == 'add': op = '+'
    if op == 'sub': op = '-'
    if op == 'mul': op = '*'
    if op == 'div': op = '/'
    if op == 'ge': op = '>='
    if op == 'gt': op = '>'
    if op == 'le': op = '<='
    if op == 'lt': op = '<'

    if type(left) in [int, float] and isinstance(right, CodeValue) and right.value in [int, float]:
        return CodeValue(_binary_ops[op](left, right.value))

    if type(right) in [int, float] and isinstance(left, CodeValue) and left.value in [int, float]:
        return CodeValue(_binary_ops[op](left.value, right))

    if type(left) in [int, float] and type(right) in [int, float]:
        return CodeValue(_binary_ops[op](left, right))

    if not isinstance(left, CodeObject):
        left = CodeValue(left)

    if not isinstance(right, CodeObject):
        right = CodeValue(right)

    if isinstance(left, CodeValue) and isinstance(right, CodeValue) and op in _binary_ops:
        L, R = left.value, right.value
        if type(L) in [int, float] and type(R) in [int, float]:
            return CodeValue(_binary_ops[op](L, R))

    if isinstance(left, CodeValue) and left.value in [0, 1]:
        if left.value == 0 and op in ['+']:
            return right
        if left.value == 0 and op in ['*', '/']:
            return left
        if left.value == 1 and op in ['*']:
            return right
        if op == '**':
            return left

    if isinstance(right, CodeValue) and right.value in [0, 1]:
        if right.value == 0 and op in ['+', '-']:
            return left
        if right.value == 0 and op in ['*']:
            return right
        if right.value == 1 and op in ['*', '/', '**']:
            return left

    return CodeBinary(left, op, right)

def makeSubscript(seq, index):
    if not isinstance(index.code_type, IntegerType):
        if isinstance(index, CodeValue):
            index = CodeValue(int(index.value))
        else:
            index = CodeFunctionCall('int', [index])
    elif isinstance(index, CodeValue):
        if isinstance(seq, CodeValue) and type(seq.value) is list:
            return seq.value[index.value]
        elif isinstance(seq, CodeVector):
            return seq.items[index.value]
    if isinstance(seq, CodeValue) and len(set(seq.value)) == 1:
        return CodeValue(seq.value[0])
    return CodeSubscript(seq, index)

def makeVector(items: list):
    if all([isinstance(item, CodeValue) for item in items]):
        return CodeValue([item.value for item in items])
    else:
        return CodeVector(items)
