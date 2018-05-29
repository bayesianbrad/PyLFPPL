#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 29. Nov 2017, Tobias Kohn
# 24. Jan 2018, Tobias Kohn
#
class Sequence(object):

    def __repr__(self):
        return repr(self.data)

    def __getitem__(self, item):
        return self.data[item]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    @property
    def head(self):
        return self.data[0]

    @property
    def tail(self):
        return self.data[1:]


class Form(Sequence):

    def __init__(self, data, line_number:int=-1):
        self.data = data
        self.line_number = line_number

    def __getitem__(self, item):
        if isinstance(item, slice):
            return Form(self.data[item])
        else:
            return self.data[item]

class Value(object):

    def __init__(self, value, line_number:int=-1):
        self.value = value
        self.line_number = line_number

    def __repr__(self):
        return repr(self.value)

    def __eq__(self, other):
        if isinstance(other, Value):
            return self.value == other.value
        else:
            return False


class Vector(Sequence):

    def __init__(self, data, line_number:int=-1):
        self.data = data
        self.line_number = line_number

    def __repr__(self):
        return "[{}]".format(', '.join([repr(item) for item in self.data]))


class Symbol(object):

    _symbols = {}

    def __new__(cls, name, *args, **kwargs):
        if name in Symbol._symbols.keys():
            return Symbol._symbols[name]
        if type(name) is Symbol:
            return name
        return super(Symbol, cls).__new__(cls)

    def __init__(self, name: str):
        assert(type(name) is str)
        self.name = name
        if name not in Symbol._symbols.keys():
            Symbol._symbols[name] = self

        # These special forms here are actually defined below but IDEs are happier if we define
        # some form here.
        self.DEF = "def"
        self.DEREF = "deref"
        self.IF = "if"
        self.DO = "do"
        self.LET = "let"
        self.QUOTE = "quote"
        self.VAR = "var"
        self.FN = "fn"
        self.LOOP = "loop"
        self.RECUR = "recur"
        self.THROW = "throw"
        self.TRY = "try"
        self.MONITOR_ENTER = "monitor-enter"
        self.MONITOR_EXIT = "monitor-exit"
        self.VAR = "var"
        self.VECTOR = "vector"

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(("$SYMBOL", self.name))

    def __eq__(self, other):
        if isinstance(other, Symbol):
            return self.name == other.name
        else:
            return False

Symbol.CASE = Symbol('case')
Symbol.CONCAT = Symbol('concat')
Symbol.COND = Symbol('cond')
Symbol.CONS = Symbol('cons')
Symbol.DECLARE = Symbol('declare')
Symbol.DEF = Symbol('def')
Symbol.DEF_MACRO = Symbol('defmacro')
Symbol.DEFN = Symbol('defn')
Symbol.DEFRECORD = Symbol('defrecord')
Symbol.DEREF = Symbol('deref')
Symbol.DO = Symbol('do')
Symbol.FN = Symbol('fn')
Symbol.FOR = Symbol('for')
Symbol.FOR_EACH = Symbol("for-each")
Symbol.IF = Symbol('if')
Symbol.IF_NOT = Symbol('if-not')
Symbol.LET = Symbol('let')
Symbol.LIST = Symbol('list')
Symbol.LOOP = Symbol('loop')
Symbol.NS = Symbol('ns')
Symbol.QUOTE = Symbol('quote')
Symbol.RECUR = Symbol('recur')
Symbol.SEQ = Symbol('seq')
Symbol.STR = Symbol('str')
Symbol.VAR = Symbol('var')
Symbol.VEC = Symbol('vec')
Symbol.VECTOR = Symbol('vector')

Symbol.IS_SEQ = Symbol('seq?')
Symbol.IS_VECTOR = Symbol('vector?')

Symbol.PLUS = Symbol('+')
Symbol.MINUS = Symbol('-')
Symbol.MULTIPLY = Symbol('*')
Symbol.DIVIDE = Symbol('/')
Symbol.AND = Symbol('and')
Symbol.OR = Symbol('or')
Symbol.NOT = Symbol('not')
Symbol.XOR = Symbol('xor')
Symbol.EQ = Symbol('=')
Symbol.LT = Symbol('<')
Symbol.GT = Symbol('>')
Symbol.LE = Symbol('<=')
Symbol.GE = Symbol('>=')