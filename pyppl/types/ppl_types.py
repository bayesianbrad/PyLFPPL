#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 07. Feb 2018, Tobias Kohn
# 16. Mar 2018, Tobias Kohn
#
from typing import Optional

class Type(object):

    def __init__(self, *, name:str, base=None):
        assert(type(name) is str)
        assert(base is None or isinstance(base, Type))
        self.name = name # type:str
        self.base = base # type:Type

    def __contains__(self, item):
        if item is self:
            return True
        elif isinstance(item, Type):
            return item.base in self
        elif hasattr(item, 'get_type'):
            return self.__contains__(getattr(item, 'get_type')())
        elif hasattr(item, '__type__'):
            return self.__contains__(getattr(item, '__type__'))
        else:
            return False

    def __eq__(self, other):
        return other is self

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name

    def union(self, other):
        if isinstance(other, Type):
            if other in self:
                return self
            elif self in other:
                return other
            elif self.base is not None and other.base is not None:
                return self.base.union(other.base)
            else:
                return AnyType
        else:
            raise RuntimeError("must be a type: '{}'".format(type(other)))

    @property
    def dimension(self):
        return None

    # We implement common operations on the types for easy type inference

    def __add__(self, other):
        from . import ppl_type_operations
        if isinstance(other, Type):
            return ppl_type_operations.add(self, other)
        else:
            return NotImplemented

    def __sub__(self, other):
        from . import ppl_type_operations
        if isinstance(other, Type):
            return ppl_type_operations.sub(self, other)
        else:
            return NotImplemented

    def __mul__(self, other):
        from . import ppl_type_operations
        if isinstance(other, Type):
            return ppl_type_operations.mul(self, other)
        else:
            return NotImplemented

    def __truediv__(self, other):
        from . import ppl_type_operations
        if isinstance(other, Type):
            return ppl_type_operations.div(self, other)
        else:
            return NotImplemented

    def __floordiv__(self, other):
        from . import ppl_type_operations
        if isinstance(other, Type):
            return ppl_type_operations.idiv(self, other)
        else:
            return NotImplemented

    def __mod__(self, other):
        from . import ppl_type_operations
        if isinstance(other, Type):
            return ppl_type_operations.mod(self, other)
        else:
            return NotImplemented

    def __neg__(self):
        from . import ppl_type_operations
        return ppl_type_operations.neg(self)

    def __pos__(self):
        from . import ppl_type_operations
        return ppl_type_operations.pos(self)

    def __pow__(self, power, modulo=None):
        return self


#######################################################################################################################

class SequenceType(Type):

    def __init__(self, *, name:str, base=None, item_type:Type=None, size:int=None,
                 recursive:bool=False):
        super().__init__(name=name, base=base)
        if recursive:
            assert(item_type is None)
            assert(size is None)
            self.item_type = self
        else:
            self.item_type = item_type
        self.size = size
        self.recursive = recursive
        self._sub_types = {}
        self._sequence_type = base._sequence_type if isinstance(base, SequenceType) else self
        assert(self.item_type is None or isinstance(self.item_type, Type))
        assert(size is None or (type(size) is int and size >= 0))

    def __eq__(self, other):
        if other is self:
            return True
        elif isinstance(other, SequenceType) and self._sequence_type is other._sequence_type:
            return other.item_type == self.item_type and other.size == self.size
        else:
            return False

    def __hash__(self):
        if self.item_type is None:
            return hash(self.name)
        elif self.size is None:
            return hash((self.name, hash(self.item_type)))
        else:
            return hash((self.name, hash(self.item_type), self.size))

    def __repr__(self):
        if self.item_type is None or self.recursive:
            return self.name
        elif self.size is None:
            return "{}[{}]".format(self.name, repr(self.item_type))
        else:
            return "{}[{};{}]".format(self.name, repr(self.item_type), self.size)

    def __getitem__(self, item):
        if self.recursive:
            raise TypeError("recursive sequence-type cannot have specialized type")

        if self.item_type is None:
            if type(item) is tuple and len(item) == 2 and isinstance(item[0], Type) and type(item[1]) is int:
                result = self.__getitem__(item[0])
                return result.__getitem__(item[1])

            elif isinstance(item, SequenceType):
                return SequenceType(name=self.name, base=self, item_type=item)

            elif isinstance(item, Type):
                if item not in self._sub_types:
                    self._sub_types[item] = SequenceType(name=self.name, base=self, item_type=item)
                return self._sub_types[item]

        elif self.size is None:
            if type(item) is int and item >= 0:
                if 0 <= item <= 3:
                    if item not in self._sub_types:
                        self._sub_types[item] = SequenceType(name=self.name, base=self,
                                                             item_type=self.item_type, size=item)
                    return self._sub_types[item]
                else:
                    return SequenceType(name=self.name, base=self, item_type=self.item_type, size=item)

        raise TypeError("cannot construct '{}'-subtype of '{}'".format(item, self))

    def __contains__(self, item):
        if item is self:
            return True

        elif isinstance(item, SequenceType) and item._sequence_type is self._sequence_type:
            if self.item_type is None:
                return True
            elif item.item_type in self.item_type and (self.size is None or self.size == item.size):
                return True
            else:
                return False

        elif isinstance(item, Type):
            return item is NullType

        elif hasattr(item, 'get_type'):
            return self.__contains__(getattr(item, 'get_type')())

        elif hasattr(item, '__type__'):
            return self.__contains__(getattr(item, '__type__'))

        else:
            return False

    def slice(self, start, stop):
        if type(start) is int and type(stop) is int:
            new_size = stop - start
        elif type(start) is int and type(self.size) is int:
            new_size = self.size - start
        elif type(stop) is int:
            new_size = stop
        else:
            new_size = None

        return SequenceType(name=self.name, base=self.base, item_type=self.item_type, size=new_size)

    @property
    def item(self):
        return self.item_type if self.item_type is not None else AnyType

    @property
    def dimension(self):
        if isinstance(self.item_type, SequenceType) and self.size is not None:
            dim = self.item_type.dimension
            if type(dim) is tuple:
                return (self.size, *dim)
            elif type(dim) is int:
                return self.size, dim
            else:
                return self.size

        elif self.size is not None:
            return self.size

        else:
            return None


#######################################################################################################################

class FunctionType(Type):

    def __init__(self, *, name:str, base=None, param_count:int=None, has_var_args:bool=False, has_kw_args:bool=False,
                 parameter_types:list=None, result_type:Type=None):
        super(FunctionType, self).__init__(name=name, base=base)
        self._empty = param_count is None and parameter_types is None and result_type is None
        if result_type is None:
            result_type = AnyType
        if parameter_types is not None:
            if type(parameter_types) is tuple:
                parameter_types = list(parameter_types)
            if param_count is None:
                param_count = len(parameter_types)
            else:
                assert(len(parameter_types) == param_count)
        else:
            if param_count is not None and param_count > 0:
                parameter_types = [AnyType] * param_count
            else:
                param_count = 0
                parameter_types = []
        self.parameter_types = parameter_types # type:list
        self.result_type = result_type
        self.param_count = param_count
        self.has_var_args = has_var_args
        self.has_kw_args = has_kw_args
        assert(isinstance(result_type, Type))
        assert(type(self.param_count) is int)
        assert(type(self.has_var_args) is bool and type(self.has_kw_args) is bool)
        assert(type(self.parameter_types) is list)
        assert(all([isinstance(item, Type) for item in self.parameter_types]))

    def __eq__(self, other):
        if other is self:
            return True
        elif isinstance(other, FunctionType):
            return self.result_type == other.result_type and \
                   self.param_count == other.param_count and \
                   all([a == b for a, b in zip(self.parameter_types, other.parameter_types)]) and \
                   self.has_kw_args == other.has_kw_args and \
                   self.has_var_args == other.has_var_args
        else:
            return False

    def __hash__(self):
        return hash((tuple(self.parameter_types), self.result_type, self.has_var_args, self.has_kw_args))

    def __repr__(self):
        return "({})=>{}".format(', '.join([repr(item) for item in self.parameter_types]), repr(self.result_type))

    def __contains__(self, item):
        if isinstance(item, FunctionType):
            if item == self:
                return True

            if item.result_type in self.result_type:
                if self.param_count == item.param_count:
                    return all([a in b for a, b in zip(self.parameter_types, item.parameter_types)])

        return False

    def __create_function_type(self, *, param_count=None, parameters=None, result):
        return FunctionType(name=self.name, base=self, param_count=param_count,
                            parameter_types=parameters, result_type=result)

    def __getitem__(self, item):
        if self._empty:
            if type(item) is tuple and len(item) >= 2 and isinstance(item[-1], Type):
                result = item[-1]
                args = item[:-1]

                if len(args) == 1 and type(args[0]) is int:
                    return self.__create_function_type(param_count=args[0], result=result)

                elif all([isinstance(arg, Type) for arg in args]):
                    return self.__create_function_type(parameters=args, result=result)

                elif len(args) == 1 and type(args[0]) in (tuple, list) and len(args[0]) == 0:
                    return self.__create_function_type(param_count=0, result=result)

                elif len(args) == 1 and type(args[0]) in (tuple, list) and \
                        all([isinstance(arg, Type) for arg in args[0]]):
                    return self.__create_function_type(parameters=args[0], result=result)

            elif isinstance(item, Type):
                return self.__create_function_type(param_count=0, result=item)

        raise TypeError("cannot construct '{}'-subtype of '{}'".format(item, self))

    @property
    def arg_count(self):
        return self.param_count

    def union(self, other):
        if isinstance(other, FunctionType):
            if other == self:
                return self

            elif self.param_count == other.param_count and self.has_var_args == other.has_var_args and \
                    self.has_kw_args == other.has_kw_args:
                params = [p.union(q) for p, q in zip(self.parameter_types, other.parameter_types)]
                result = self.result_type.union(other.result_type)
                return self.__create_function_type(parameters=params, result=result)

            return Function

        return super(FunctionType, self).union(other)


#######################################################################################################################

AnyType  = Type(name='Any')
NullType = Type(name='Null', base=AnyType)

Numeric = Type(name='Numeric', base=AnyType)
Float   = Type(name='Float',   base=Numeric)
Integer = Type(name='Integer', base=Float)
Boolean = Type(name='Boolean', base=Integer)

List    = SequenceType(name='List',   base=AnyType)
Tuple   = SequenceType(name='Tuple',  base=AnyType)
String  = SequenceType(name='String', base=AnyType, recursive=True)
Dict    = SequenceType(name='Dict',   base=AnyType)

Array   = SequenceType(name='Array',  base=AnyType)
Tensor  = SequenceType(name='Tensor', base=AnyType)

Function = FunctionType(name='Function', base=AnyType)

#######################################################################################################################

_types = {
    bool: Boolean,
    float: Float,
    int: Integer,
    list: List,
    str: String,
    tuple: Tuple,
}

def from_python(value):
    if value.__hash__ is not None and value in _types:
        return _types[value]

    t = type(value)
    if t in [list, tuple]:
        item = union(*[from_python(item) for item in value])
        if t is list:
            return List[item][len(value)]

        elif t is tuple:
            return Tuple[item][len(value)]

    elif t in _types:
        return _types[t]

    else:
        return AnyType

def makeArray(base):
    if isinstance(base, SequenceType):
        item = makeArray(base.item) if isinstance(base.item, SequenceType) else base.item
        return Array[item, base.size]
    else:
        return Array[base, 1]

def makeTensor(base, base_type:Optional[str]=None):
    if base_type is not None:
        if base in ('FloatTensor', 'DoubleTensor', 'HalfTensor'):
            b_type = Tensor[Float]
        elif base in ('IntTensor', 'ShortTensor', 'ByteTensor', 'LongTensor'):
            b_type = Tensor[Integer]
        else:
            b_type = Tensor
    else:
        b_type = None

    if isinstance(base, SequenceType):
        if b_type is None:
            b_type = base.item
        item = makeTensor(base.item, base_type) if isinstance(base.item, SequenceType) else b_type
        return Tensor[item, base.size]
    elif base_type is not None:
        return Tensor[b_type, 1]
    else:
        return Tensor[base, 1]

def union(*types):
    types = [t for t in types if t is not None]
    if len(types) > 0:
        result = types[0]
        for t in types[1:]:
            result = result.union(t)
        return result

    else:
        return AnyType
