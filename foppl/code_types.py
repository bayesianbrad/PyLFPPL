#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 16. Jan 2018, Tobias Kohn
# 01. Feb 2018, Tobias Kohn
#
class AnyType(object):

    def __new__(cls, *args, **kwargs):
        if cls is AnyType and hasattr(cls, '__singleton__'):
            return cls.__singleton__
        return super(AnyType, cls).__new__(cls)

    def __hash__(self):
        return hash(('$type$', self.__class__.__name__))

    def __eq__(self, other):
        if not isinstance(other, AnyType) and issubclass(other, AnyType):
            other = other()
        return other is self

    def __repr__(self):
        name = self.__class__.__name__
        if name.endswith("Type"):
            name = name[:-4]
        return "<{}>".format(name)

    def accept(self, other):
        if not isinstance(other, AnyType) and issubclass(other, AnyType):
            other = other()
        return isinstance(other, self.__class__)

    def apply_binary(self, op: str, other):
        raise TypeError("incompatible types for operation '{}': '{}' and '{}'".format(op, self, other))

    def union(self, other):
        cls1 = self.__class__
        cls2 = other.__class__
        if issubclass(cls1, cls2): return self
        if issubclass(cls2, cls1): return other
        while cls1 is not AnyType and cls2 is not AnyType:
            if issubclass(cls1, cls2):
                return cls2()
            if issubclass(cls2, cls1):
                return cls1()
            cls1 = cls1.__base__
            cls2 = cls2.__base__
        return AnyType()

    def dimension(self):
        return 0

def __instantiate__(tp):
    if type(tp) is list:
        return [__instantiate__(t) for t in tp]
    elif isinstance(tp, AnyType):
        return tp
    elif issubclass(tp, AnyType):
        return tp()
    else:
        raise TypeError("'{}' is not a valid type".format(repr(tp)))


AnyType.__singleton__ = AnyType()


def union(*types):
    if len(types) > 0:
        result = types[0]
        for t in types[1:]:
            result = result.union(t)
        return result
    else:
        return AnyType()


######### BASE CLASSES #########

class FunctionType(AnyType):

    def accept(self, other):
        return self == other

    def result_type(self, args: list):
        return AnyType()

class SimpleType(AnyType):

    def __new__(cls, *args, **kwargs):
        if hasattr(cls, '__singleton__') and isinstance(cls.__singleton__, cls):
            return cls.__singleton__
        return super(SimpleType, cls).__new__(cls, *args)

    def __init__(self):
        self.__class__.__singleton__ = self

class SequenceType(AnyType):

    def __new__(cls, item_type, size, *args, **kwargs):
        if type(size) is not int or size < 0: size = None
        item_type = __instantiate__(item_type)
        field = '__{}_singletons__'.format(cls.__name__[:-4])
        if not hasattr(cls, field):
            setattr(cls, field, {})
        singletons = getattr(cls, field)
        if (item_type, size) in singletons:
            return singletons[item_type, size]
        return super(SequenceType, cls).__new__(cls, *args)

    def __init__(self, item_type, size: int):
        if type(size) is not int or size < 0: size = None
        item_type = __instantiate__(item_type)
        field = '__{}_singletons__'.format(self.__class__.__name__[:-4])
        singletons = getattr(self.__class__, field)
        singletons[item_type, size] = self
        self.item_type = item_type
        self.size = size

    def __repr__(self):
        name = self.__class__.__name__
        if name.endswith("Type"):
            name = name[:-4]
        return "<{}[{}x{}]>".format(name, self.size if self.size else '?', self.item_type)

    def accept(self, other):
        other = __instantiate__(other)
        if isinstance(other, self.__class__) and self.item_type.accept(other.item_type):
            return self.size == other.size or self.size is None
        else:
            return False

    def union(self, other):
        if isinstance(other, SequenceType):
            size = self.size if self.size == other.size else None
            item_type = self.item_type.union(other.item_type)
            if self.__class__ is other.__class__:
                return self.__class__(item_type, size)
            else:
                return SequenceType(item_type, size)
        return super(SequenceType, self).union(other)

    def dimension(self):
        d = self.item_type.dimension()
        if type(d) is tuple:
            return (self.size, *d)
        elif d > 0:
            return (self.size, d)
        else:
            return self.size


class TupleType(AnyType):
    pass


######### SIMPLE TYPES #########

class NumericType(SimpleType):

    def apply_binary(self, op: str, other):
        if isinstance(other, NumericType):
            return self.union(other)
        else:
            return super(NumericType, self).apply_binary(op, other)

class FloatType(NumericType):
    pass

class IntegerType(FloatType):

    def apply_binary(self, op: str, other):
        if isinstance(other, StringType) and op == '*':
            return other
        else:
            return super(IntegerType, self).apply_binary(op, other)

class BooleanType(IntegerType):
    pass

class StringType(SimpleType):

    def apply_binary(self, op: str, other):
        if isinstance(other, StringType) and op == '+':
            return self
        elif isinstance(other, IntegerType) and op == '*':
            return self
        else:
            return super(StringType, self).apply_binary(op, other)

class NullType(SimpleType):
    pass

######### SEQUENCE TYPES #########

class ListType(SequenceType):

    @staticmethod
    def fromList(types):
        if len(types) > 0:
            for i in range(len(types)):
                if not isinstance(types[i], AnyType) and issubclass(types[i], AnyType):
                    types[i] = types[i]()
            item_type = types[0]
            for t in types[1:]:
                item_type = item_type.union(t)
        else:
            item_type = AnyType()
        return ListType(item_type, len(types))


######### DISTRIBUTION TYPE #########

class DistributionType(AnyType):

    def __init__(self, distribution, args:list):
        self.args = __instantiate__(args)
        self.result = distribution.get_sample_type(self.args)

    def result_type(self):
        return self.result


######### FUNCTIONAL TYPES #########

class TypedFunctionType(FunctionType):

    def __init__(self, args: list, result):
        self.arg_count = len(args)
        self.args = __instantiate__(args)
        self.result = __instantiate__(result)

    def __eq__(self, other):
        if other is self:
            return True
        elif isinstance(other, TypedFunctionType) and other.arg_count == self.arg_count and other.result == self.result:
            return all([u == v for u, v in zip(self.args, other.args)])
        else:
            return False

    def __repr__(self):
        return "({}) -> {}".format(', '.join([repr(a) for a in self.args]), repr(self.result))

    def result_type(self, args: list):
        if len(args) == len(self.args) and all([v.accept(u) for u, v in zip(args, self.args)]):
            return self.result
        else:
            raise TypeError("wrong number or type of arguments")


class UntypedFunctionType(FunctionType):

    def __init__(self, arg_count: int, result, varargs: bool=False):
        self.arg_count = arg_count
        self.result = __instantiate__(result)
        self.varargs = varargs

    def __eq__(self, other):
        if other is self:
            return True
        elif isinstance(other, UntypedFunctionType) and other.arg_count == self.arg_count and other.result == self.result:
            return True
        else:
            return False

    def __repr__(self):
        args = [repr(AnyType()) for _ in range(self.arg_count)]
        return "({}) -> {}".format(', '.join(args), repr(self.result))

    def accept(self, other):
        if isinstance(other, UntypedFunctionType):
            pass
        elif isinstance(other, TypedFunctionType):
            pass
        else:
            return False

    def result_type(self, args: list):
        if len(args) == self.arg_count:
            return self.result
        elif self.varargs and len(args) >= self.arg_count:
            return self.result
        else:
            raise TypeError("wrong number or type of arguments")


####################################

__primitive_types = {
    float: FloatType,
    int: IntegerType,
    str: StringType
}

def apply_binary(type1: AnyType, op: str, type2: AnyType):
    if type1:
        return type1.apply_binary(op, type2)
    else:
        return AnyType()

def get_code_type_for_value(value):
    t = type(value)
    if value is None:
        return NullType()
    elif t in __primitive_types:
        return __primitive_types[t]()
    elif t is list:
        return ListType.fromList([get_code_type_for_value(v) for v in value])
    return AnyType()

####################################

if __name__ == "__main__":
    s = FloatType()
    t = IntegerType()
    u = ListType(FloatType, 5)
    v = ListType(IntegerType, 5)
    print(s, id(s))
    print(t, id(t))
    print(s is t)
    print(s.accept(t))
    print(t.accept(s))
    print(u.accept(v))
    print(v.accept(u))
    print(ListType.fromList([ListType(IntegerType, 2), ListType(IntegerType, 2)]))
