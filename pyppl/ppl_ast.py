#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 07. Feb 2018, Tobias Kohn
# 28. Mar 2018, Tobias Kohn
#
from typing import Optional
import enum
from ast import copy_location as _cl
import inspect as _inspect

class AstNode(object):
    """
    The `AstNode` is the base-class for all AST-nodes. You will typically not instantiate an object of this class,
    but derive a specific AST-node from it.
    """

    _attributes = { 'col_offset', 'lineno' }
    original_name = None
    tag = None

    def get_fields(self):
        fields = set(self.__dict__).difference(set(AstNode.__dict__))
        fields = [name for name in fields if len(name) > 0 and not name.startswith('_')]
        return fields

    def set_field_values(self, source):
        if isinstance(source, self.__class__):
            for field in self.get_fields():
                setattr(self, field, getattr(source, field))
        elif type(source) is dict:
            for field in source:
                if hasattr(self, field):
                    setattr(self, field, source[field])
        else:
            raise RuntimeError("cannot set fields from source '{}'".format(repr(source)))

    def get_children(self):
        """
        Returns a list of all fields, which are either `AstNode`-objects, or sequences (list/tuples) of such objects.

        :return: A list of strings denoting fields, which are `AstNode`-objects or sequences thereof.
        """
        def is_valid(name):
            field = getattr(self, name, None)
            if isinstance(field, AstNode):
                return True
            elif hasattr(field, '__iter__') and all([isinstance(item, AstNode) for item in field]):
                return True
            else:
                return False

        return [item for item in self.get_fields() if is_valid(item)]

    def get_ast_children(self):
        """
        Returns a flat list of all fields/children, which are `AstNode`-objects.

        :return: A (possibly empty) list of `AstNode`-objects.
        """
        result = []
        for name in self.get_fields():
            field = getattr(self, name, None)
            if isinstance(field, AstNode):
                result.append(field)
            elif hasattr(field, '__iter__'):
                for item in field:
                    if isinstance(item, AstNode):
                        result.append(item)
        return result

    def get_type(self):
        """
        Returns the type of this node.

        :return: Either an instance of `Type` (see `ppl_types`), or `None`.
        """
        return getattr(self, '__type__', None)

    def get_visitor_names(self):
        """
        Returns an ordered list of possible names for the visit-methods to be called by `visit`.

        We want to be flexible and provide a hierarchy of method names to try out. Take, for instance, an AST-node
        for a FOR-loop. The visit-method to call might then be called `visit_ForLoop`, `visit_for_loop`, or we might
        end up having a more generic `visit_loop` to call.

        The default implementation given here provides various possibilities based on the name of the instance's class.
        If, say, the node is of class `AstForLoop`, then we try the following names:
        `visit_AstForLoop`, `visit_astforloop`, `visit_for_loop`, `visit_forloop`
        Be overriding this method, you might change the names altogether, or insert a more general name such as
        `visit_loop` or `visit_compound_statement`.

        :return:   A list of strings with possible method names.
        """
        name = self.__class__.__name__
        if name.startswith("Ast"):
            name = name[3:]
        elif name.endswith("Node"):
            name = name[:-4]
        if name.islower():
            result = ['visit_' + name]
        else:
            name2 = ''.join([n if n.islower() else "_" + n.lower() for n in name])
            while name2.startswith('_'): name2 = name2[1:]
            result = ['visit_' + name, 'visit_' + name.lower(), 'visit_' + name2]
        return result

    def __get_envelop_method_names(self):
        """
        Returns a list of two names `enter_XXX` and `leave_XXX`, where the `XXX` stands for the name of the class.
        This is used inside the `visit`-method.

        :return:  A list with exactly two strings.
        """
        name = self.__class__.__name__
        if name.startswith("Ast"):
            name = name[3:]
        elif name.endswith("Node"):
            name = name[:-4]
        name = name.lower()
        return ['enter_' + name, 'leave_' + name]

    def visit(self, visitor):
        """
        The visitor-object given as argument must provide at least one `visit_XXX`-method to be called by this method.
        Possible names for the `visit_XXX`-method are given by `get_visitor_names()`. Override that method in order
        to control which visitor-method is actually called.

        If the visitor does not provide any specific `visit_XXX`-method to be called, the method will try and call
        `visit_node` or `generic_visit`, respectively.

        It is possible to provide, in addition to a `visit_XXX`-method, two methods `enter_XXX` and `leave_XXX`, which
        are called right before, and right after, respectively, the `visit_XXX`-method itself is called. They do not
        replace but supplement the `visit_XXX`-method.

        :param visitor: An object with a `visit_XXX`-method.
        :return:        The result returned by the `visit_XXX`-method of the visitor.
        """
        visit_children_first = getattr(visitor, '__visit_children_first__', False) is True
        lm_method = getattr(visitor, 'set_current_line_number', None)
        method_names = self.get_visitor_names() + ['visit_node', 'generic_visit']
        methods = [getattr(visitor, name, None) for name in method_names]
        methods = [name for name in methods if name is not None]
        env_methods = [getattr(visitor, name, None) for name in self.__get_envelop_method_names()]
        env_methods = [name for name in env_methods if name is not None]
        if len(methods) == 0 and callable(visitor):
            if visit_children_first:
                self.visit_children(visitor)
            return visitor(self)
        elif len(methods) > 0:
            if getattr(self, 'verbose', False) is True or getattr(visitor, 'verbose', False) is True:
                print("calling {}".format(methods[0]))
            if len(env_methods) == 2:
                obj = self
                if lm_method is not None and hasattr(self, 'lineno'):
                    lm_method(self.lineno)
                env_methods[0](self)
                try:
                    if visit_children_first:
                        self.visit_children(visitor)
                    if lm_method is not None and hasattr(self, 'lineno'):
                        lm_method(self.lineno)
                    result = methods[0](self)
                    if isinstance(result, self.__class__):
                        obj = result
                finally:
                    env_methods[1](obj)
                return result
            else:
                if visit_children_first:
                    self.visit_children(visitor)
                if lm_method is not None and hasattr(self, 'lineno'):
                    lm_method(self.lineno)
                return methods[0](self)
        else:
            raise RuntimeError("visitor '{}' has no visit-methods to call".format(type(visitor)))

    def visit_children(self, visitor):
        """
        Goes through all fields provided by the method `get_fields`, which are objects derived from `AstNode`.
        For each such object, the `visit`-method (see above) is called.

        :param visitor: An object with `visit_XXX`-methods to be called by the children of this node.
        :return:        A list with the values returned by the called `visit_XXX`-methods.
        """
        result = []
        for name in self.get_fields():
            item = getattr(self, name, None)
            if isinstance(item, AstNode) or type(item) in (list, tuple):
                result.append(visitor.visit(item))
        return result

    def visit_attribute(self, visitor, attr_name:str, default=None):
        """
        Sets an attribute on each node in the AST, based on the provided visitor (see `visit`-method above).

        :param visitor:    An object with `visit_XXX`-methods to be called.
        :param attr_name:  The name of the attribute to set, must be a string.
        :return:           The value of the attribute set.
        """
        assert type(attr_name) is str
        for name in self.get_fields():
            item = getattr(self, name, default)
            if isinstance(item, AstNode):
                item.visit_attribute(visitor, attr_name)
            elif hasattr(item, '__iter__'):
                for node in item:
                    if isinstance(node, AstNode):
                        node.visit_attribute(visitor, attr_name)
        result = self.visit(visitor)
        result = result if result is not self else None
        setattr(self, attr_name, result)
        return result

    def append(self, node):
        """
        Append another node to this one. In most cases, this means that a new `AstBody` with two items is created,
        i.e. `x.append(y)` -> `AstBody([x, y])`.

        In case the current node is an `if`-node, the second node will be appended to both branches.

        :param node:  Another node to be appended to the current node.
        :return:      A node that contains both nodes.
        """
        if node is not None:
            return _cl(makeBody(self, node), self)
        else:
            return self

    def equals(self, node):
        try:
            for attr in self.get_fields():
                if attr in self._attributes: continue
                attr_a = getattr(self, attr)
                attr_b = getattr(node, attr)
                if type(attr_a) in (list, tuple) and type(attr_b) in (list, tuple):
                    for a, b in zip(attr_a, attr_b):
                        if a != b:
                            return False
                elif attr_a != attr_b:
                    return False
            return True
        except:
            return False

    def __eq__(self, other):
        return self.equals(other) if isinstance(other, self.__class__) else False

    def clone(self, **kwargs):
        init_method = getattr(self, '__init__', None)
        if init_method is not None:
            args = { arg: getattr(self, arg, None) for arg in _inspect.getfullargspec(init_method).args if arg != 'self' }
            for arg in args:
                if arg in kwargs:
                    args[arg] = kwargs[arg]
            result = self.__class__(**args)
        else:
            result = self.__class__()
        fields = set(self.__dict__).difference(set(result.__dict__))
        for field in fields:
            setattr(result, field, getattr(self, field))
        for key in kwargs:
            setattr(result, key, kwargs[key])
        return result


class Visitor(object):
    """
    There is no strict need to derive a visitor or walker from this base class. It does, however, provide a
    default implementation for `visit` as well as `visit_node`.
    """

    def set_current_line_number(self, lineno:int):
        if hasattr(self, 'current_lineno'):
            self.current_lineno = lineno

    def visit(self, ast):
        if ast is None:
            return None
        elif type(ast) in (bool, complex, float, int, str):
            return None
        elif isinstance(ast, AstNode):
            return ast.visit(self)
        elif type(ast) is dict:
            return { key: self.visit(ast[key]) for key in ast }
        elif type(ast) is list:
            return [self.visit(item) for item in ast]
        elif type(ast) is tuple:
            return tuple([self.visit(item) for item in ast])
        else:
            raise TypeError("cannot walk/visit an object of type '{}'".format(type(ast)))

    def visit_node(self, node:AstNode):
        node.visit_children(self)
        return node


#######################################################################################################################

class Scope(object):

    def __init__(self, prev, name:Optional[str]=None, lineno:Optional[int]=None):
        self.prev = prev
        self.name = name
        self.lineno = lineno
        self.bindings = {}
        self.protected_names = set()
        assert prev is None or isinstance(prev, Scope)
        assert name is None or type(name) is str
        assert lineno is None or type(lineno) is int

    def define(self, name:str, value):
        assert type(name) is str and str != '' and str != '_'
        self.bindings[name] = value

    def define_protected(self, name:str):
        assert type(name) is str and str != '' and str != '_'
        self.protected_names.add(name)

    def resolve(self, name:str):
        if name in self.protected_names:
            return None
        elif name in self.bindings:
            return self.bindings[name]
        elif self.prev is not None:
            return self.prev.resolve(name)
        else:
            return None

    def resolve_locally(self, name:str):
        if name in self.protected_names:
            return None
        else:
            return self.bindings.get(name, None)

    def depth(self):
        result = 1
        p = self.prev
        while p is not None:
            result += 1
            p = p.prev
        return result


class ScopeContext(object):
    """
    The `ScopeContext` is a thin layer used to support scoping in `with`-statements inside methods of
    `ScopedVisitor`, i.e. `with create_scope(): do something`.
    """

    def __init__(self, visitor):
        self.visitor = visitor

    def __enter__(self):
        return self.visitor.scope

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.visitor.leave_scope()


class ScopedVisitor(Visitor):

    def __init__(self):
        self.scope = Scope(None)
        self.global_scope = self.scope
        self.MAX_SCOPE_DEPTH = 100

    def enter_scope(self, name:Optional[str]=None):
        if self.scope.depth() >= self.MAX_SCOPE_DEPTH:
            raise RuntimeError("exceeding max scope depth")
        self.scope = Scope(self.scope, name)

    def leave_scope(self):
        self.scope = self.scope.prev
        assert(self.scope is not None)

    def create_scope(self, name:Optional[str]=None):
        self.enter_scope(name)
        return ScopeContext(self)

    def define(self, name, value, *, globally:bool=False):
        scope = self.global_scope if globally else self.scope
        if type(name) is str:
            scope.define(name, value)
        elif type(name) is tuple:
            if is_vector(value) and len(name) == len(value):
                for n, v in zip(name, value):
                    scope.define(n, v)
        else:
            return False
        return True

    def protect(self, name):
        if type(name) is str:
            self.scope.define_protected(name)
        elif type(name) is tuple:
            for n in name:
                self.protect(n)

    def define_all(self, names:list, values:list, *, vararg:Optional[str]=None):
        assert type(names) is list
        assert type(values) is list
        assert vararg is None or type(vararg) is str
        for name, value in zip(names, values):
            if isinstance(name, AstSymbol):
                name = name.name
            if type(name) is str:
                self.define(name, value)
        if vararg is not None:
            self.define(str(vararg), makeVector(values[len(names):]) if len(values) > len(names) else [])

    def resolve(self, name:str):
        return self.scope.resolve(name)

    def resolve_locally(self, name:str):
        return self.scope.resolve_locally(name)

    @property
    def is_global_scope(self):
        return self.scope.prev is None


#######################################################################################################################

class AstControl(AstNode):
    pass

class AstLeaf(AstNode):
    pass

class AstOperator(AstNode):
    pass

#######################################################################################################################

class BodyContext(enum.Enum):

    GLOBAL = 0
    FUNCTION = 1
    CONTROL = 2

#######################################################################################################################

class AstAttribute(AstNode):

    def __init__(self, base:AstNode, attr:str):
        self.base = base
        self.attr = attr
        assert isinstance(base, AstNode)
        assert type(attr) is str

    def __repr__(self):
        return "{}.{}".format(repr(self.base), self.attr)


class AstBinary(AstOperator):

    __binary_ops = {
        '+':  ('add',  lambda x, y: x + y),
        '-':  ('sub',  lambda x, y: x - y),
        '*':  ('mul',  lambda x, y: x * y),
        '/':  ('div',  lambda x, y: x / y),
        '%':  ('mod',  lambda x, y: x % y),
        '//': ('idiv', lambda x, y: x // y),
        '**': ('pow',  lambda x, y: x ** y),
        '<<': ('shl',  lambda x, y: x << y),
        '>>': ('shr',  lambda x, y: x >> y),
        '&':  ('bit_and', lambda x, y: x & y),
        '|':  ('bit_or',  lambda x, y: x | y),
        '^':  ('bit-xor', lambda x, y: x ^ y),
        'and': ('and',    lambda x, y: x and y),
        'or':  ('or',     lambda x, y: x or y),
    }

    def __init__(self, left:AstNode, op:str, right:AstNode):
        self.left = left
        self.op = op
        self.right = right
        assert isinstance(left, AstNode) and isinstance(right, AstNode)
        assert op in self.__binary_ops

    def __repr__(self):
        return "({} {} {})".format(repr(self.left), self.op, repr(self.right))

    def get_visitor_names(self):
        name = 'visit_binary_' + self.op_name
        return [name] + super(AstBinary, self).get_visitor_names()

    @property
    def op_function(self):
        return self.__binary_ops[self.op][1]

    @property
    def op_name(self):
        return self.__binary_ops[self.op][0]

    def equals(self, node):
        if self.op == node.op:
            if self.left == node.left and self.right == node.right:
                return True
            elif self.op in ('+', '*', 'and', 'or') and self.left == node.right and self.right == node.left:
                return True
        return False


class AstBody(AstNode):

    def __init__(self, items:Optional[list], context:BodyContext=None):
        if items is None:
            items = []
        self.items = [item for item in items if item is not None]
        self.context = context
        assert type(self.items) is list
        assert all([isinstance(item, AstNode) for item in self.items])
        assert all([not isinstance(item, AstBody) for item in self.items]), self.items

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        return "Body({})".format('; '.join([repr(item) for item in self.items]))

    def append(self, node):
        if len(self.items) > 0 and (isinstance(self.items[-1], AstBreak) or isinstance(self.items[-1], AstReturn)):
            return self

        elif node is not None:
            return _cl(makeBody(self.items, node), self)

        else:
            return self

    def equals(self, node):
        if len(self.items) == len(node.items):
            for i, j in zip(self.items, node.items):
                if i != j:
                    return False
            return True
        else:
            return False

    @property
    def is_empty(self):
        return len(self.items) == 0

    @property
    def last_is_return(self):
        if len(self.items) > 0:
            return isinstance(self.items[-1], AstReturn)
        else:
            return False

    @property
    def non_empty(self):
        return len(self.items) != 0


class AstBreak(AstNode):

    def __repr__(self):
        return "break"

    def append(self, _):
        return self

    def equals(self, _):
        return True


class AstCall(AstNode):

    def __init__(self, function:AstNode, args:list, keywords:Optional[list]=None, is_builtin:bool=False):
        if keywords is None:
            keywords = []
        self.function = function
        self.args = args
        self.keywords = keywords # type:list
        self.is_builtin = is_builtin
        assert isinstance(function, AstNode)
        assert all([isinstance(arg, AstNode) for arg in args])
        assert type(self.keywords) is list
        assert all([type(keyword) is str for keyword in self.keywords])
        assert type(self.is_builtin) is bool

    def __repr__(self):
        keywords = [''] * (len(self.args) - len(self.keywords)) + ['{}='.format(key) for key in self.keywords]
        args = [repr(arg) for arg in self.args]
        args = [a + b for a, b in zip(keywords, args)]
        return "{}({})".format(repr(self.function), ', '.join(args))

    def get_visitor_names(self):
        name = self.function_name
        if name is not None:
            call_name = 'visit_call_' + name
            for ch in ('+', '-', '.', '/', '*'):
                call_name = call_name.replace(ch, '_')
            result = [call_name]
            if self.is_builtin:
                builtin_name = 'visit_builtin_' + name.replace('.', '_')
                result = [builtin_name] + result
            mod_name = self.function_module
            if mod_name is not None:
                result.append('visit_call_{}_function'.format(mod_name))
            return result + super().get_visitor_names()
        else:
            return super().get_visitor_names()

    def get_position_of_arg(self, keyword:str, default:int=-1):
        if keyword in self.keywords:
            return self.pos_arg_count + self.keywords.index(keyword)
        else:
            return default

    def get_keyword_arg_value(self, keyword:str, default=None):
        if keyword in self.keywords:
            i = self.keywords.index(keyword)
            i += len(self.args) - len(self.keywords)
            return self.args[i]
        else:
            return default

    @property
    def arg_count(self):
        return len(self.args)

    @property
    def pos_arg_count(self):
        return len(self.args) - len(self.keywords)

    @property
    def function_name(self):
        if isinstance(self.function, AstSymbol):
            return self.function.original_name
        elif isinstance(self.function, AstAttribute):
            if isinstance(self.function.base, AstSymbol):
                return "{}.{}".format(self.function.base.original_name, self.function.attr)
            else:
                return None
        else:
            return None

    @property
    def function_module(self):
        if isinstance(self.function, AstSymbol):
            name = self.function.original_name
            if '.' in name:
                return name[:name.index('.')]
        elif isinstance(self.function, AstAttribute):
            if isinstance(self.function.base, AstSymbol):
                return self.function.base.name
            elif isinstance(self.function.base, AstNamespace):
                return self.function.base.name
        return None

    @property
    def has_keyword_args(self):
        return len(self.keywords) > 0

    def equals(self, node):
        if self.function == node.function and len(self.args) == len(node.args) and \
                len(self.keywords) == len(node.keywords):
            for a, b in zip(self.args, node.args):
                if a != b:
                    return False
            for a, b in zip(self.keywords, node.keywords):
                if a != b:
                    return False
            return True
        else:
            return False

    def add_keywords_to_args(self, args: list):
        if len(self.keywords) > 0:
            kw = [''] * (len(args) - len(self.keywords)) + [item+'=' for item in self.keywords]
            return [a + b for a, b in zip(kw, args)]
        return args

    @property
    def left(self):
        if self.arg_count == 2:
            return self.args[0]
        else:
            return None

    @property
    def right(self):
        if self.arg_count == 2:
            return self.args[1]
        else:
            return None


class AstCompare(AstOperator):

    __cmp_ops = {
        '==': ('eq', lambda x, y: x == y, '!='),
        '!=': ('ne', lambda x, y: x != y, '=='),
        '<':  ('lt', lambda x, y: x < y,  '>='),
        '<=': ('le', lambda x, y: x <= y, '>'),
        '>':  ('gt', lambda x, y: x > y,  '<='),
        '>=': ('ge', lambda x, y: x >= y, '<'),
        'is': ('is', lambda x, y: x is y, 'is not'),
        'in': ('in', lambda x, y: x in y, 'not in'),
        'is not': ('is_not', lambda x, y: x is not y, 'is'),
        'not in': ('not_in', lambda x, y: x not in y, 'in'),
    }

    def __init__(self, left:AstNode, op:str, right:AstNode,
                 second_op:Optional[str]=None, second_right:Optional[AstNode]=None):
        if op == '=': op = '=='
        self.left = left
        self.op = op
        self.right = right
        self.second_op = second_op
        self.second_right = second_right
        assert isinstance(left, AstNode)
        assert isinstance(right, AstNode)
        assert op in self.__cmp_ops
        assert ((second_op is None and second_right is None) or
                (second_op in self.__cmp_ops and isinstance(second_right, AstNode)))

    def __repr__(self):
        if self.second_op is not None:
            return "({} {} {} {} {})".format(
                repr(self.left), self.op, repr(self.right),
                self.second_op, repr(self.second_right)
            )
        else:
            return "({} {} {})".format(repr(self.left), self.op, repr(self.right))

    def get_visitor_names(self):
        if self.second_op is not None:
            name = 'visit_ternary_' + self.op_name + '_' + self.op_name_2
        else:
            name = 'visit_binary_' + self.op_name
        return [name] + super(AstCompare, self).get_visitor_names()

    @property
    def neg_op(self):
        return self.__cmp_ops[self.op][2]

    @property
    def op_function(self):
        return self.__cmp_ops[self.op][1]

    @property
    def op_name(self):
        return self.__cmp_ops[self.op][0]

    @property
    def op_function_2(self):
        return self.__cmp_ops[self.second_op][1] if self.second_op is not None else None

    @property
    def op_name_2(self):
        return self.__cmp_ops[self.second_op][0] if self.second_op is not None else None

    @property
    def is_equality_const_test(self):
        return self.op == '==' and self.second_op is None and (is_constant(self.left) or is_constant(self.right))


class AstDef(AstNode):

    _attributes = {'col_offset', 'lineno', 'original_name'}

    def __init__(self, name:str, value:AstNode, global_context:bool=True, original_name:Optional[str]=None):
        self.name = name
        self.value = value
        self.global_context = global_context
        self.original_name = name if original_name is None else original_name
        assert type(name) is str
        assert isinstance(value, AstNode)
        assert type(global_context) is bool

    def __repr__(self):
        name = self.name
        if self.global_context:
            name = "def " + name
        return "{} := {}".format(name, repr(self.value))

    @property
    def is_function_def(self):
        return isinstance(self.value, AstFunction)


class AstDict(AstNode):

    def __init__(self, items:dict):
        self.items = items
        assert type(items) is dict
        assert all([type(key) in [bool, complex, float, int, str] and isinstance(self.items[key], AstNode)
                    for key in self.items])

    def __repr__(self):
        items = ["{}: {}".format(key, repr(self.items[key])) for key in self.items]
        return "{" + (', '.join(items)) + "}"

    def __len__(self):
        return len(self.items)

    def equals(self, node):
        if len(self.items) == len(node.items):
            for key in self.items:
                if key not in node.items or self.items[key] != node.items[key]:
                    return False
            return True
        else:
            return False


class AstFor(AstControl):

    def __init__(self, target:str, source:AstNode, body:AstNode, original_target:Optional[str]=None):
        self.target = target
        self.source = source
        self.body = body
        self.original_target = target if original_target is None else original_target
        assert type(target) is str
        assert isinstance(source, AstNode)
        assert isinstance(body, AstNode), body

    def __repr__(self):
        return "for {} in {}: ({})".format(self.target, repr(self.source), repr(self.body))


class AstFunction(AstNode):

    def __init__(self, name:Optional[str], parameters:list, body:AstNode, *, vararg:Optional[str]=None,
                 defaults:Optional[list]=None, doc_string:Optional[str]=None, f_locals:Optional[set]=None):
        if name is None:
            name = '__lambda__'
        if f_locals is None:
            f_locals = set()
        if defaults is None:
            defaults = []
        self.name = name
        self.parameters = parameters
        self.body = body
        self.vararg = vararg
        self.defaults = defaults
        self.doc_string = doc_string
        self.param_names = set(parameters + [vararg] if vararg is not None else parameters)
        self.f_locals = f_locals
        assert type(name) is str and name != ''
        assert type(parameters) is list and all([type(p) is str for p in parameters])
        assert isinstance(body, AstNode)
        assert vararg is None or type(vararg) is str
        assert type(defaults) is list and all([isinstance(item, AstNode) for item in defaults])
        assert doc_string is None or type(doc_string) is str
        assert type(f_locals) is set and all([type(n) is str for n in f_locals])
        assert self.vararg is None or len(self.defaults) == 0

    def __repr__(self):
        params = self.parameters
        if self.vararg is not None:
            params.append('*' + self.vararg)
        return "{}({}): ({})".format(self.name, ', '.join(params), repr(self.body))

    def order_arguments(self, arguments: list, keywords: list):
        parameters = self.parameters
        arg_count = len(arguments)
        param_count = len(parameters)
        if len(keywords) == 0:
            if arg_count == param_count or (arg_count > param_count and self.vararg is not None):
                if self.vararg is not None:
                    result = arguments[:param_count]
                    if arg_count > param_count:
                        result.append(makeVector(arguments[param_count:]))
                    else:
                        result.append(makeVector([]))
                    return result

                else:
                    return arguments

            elif arg_count < param_count <= arg_count + len(self.defaults):
                delta = param_count - arg_count
                return arguments + self.defaults[-delta:]

            else:
                raise TypeError("{}() takes {} positional arguments but {} were given"
                                .format(self.name, param_count, arg_count))

        else:
            delta = arg_count - len(keywords)
            result = [None] * param_count
            for i in range(delta):
                result[i] = arguments[i]
            for i in range(len(keywords)):
                key = keywords[i]
                if key not in parameters:
                    raise TypeError("{}() got an unexpected keyword argument '{}'".format(self.name, key))
                j = parameters.index(key)
                if result[j] is None:
                    result[j] = arguments[delta + i]
                else:
                    raise TypeError("{}() got multiple values for argument for '{}'".format(self.name, key))

            if self.vararg is not None:
                result.append(makeVector([]))
            elif len(self.defaults) > 0:
                delta = len(parameters) - len(self.defaults)
                for i in range(len(self.defaults)):
                    if result[delta + i] is None:
                        result[delta + i] = self.defaults[i]

            for key, item in zip(parameters, result):
                if item is None:
                    raise TypeError("{}() missing a required positional argument: '{}'".format(self.name, key))

            return result


class AstIf(AstControl):

    def __init__(self, test:AstNode, if_node:AstNode, else_node:Optional[AstNode]=None, cond_name:Optional[str]=None):
        if else_node is None:
            else_node = AstValue(None)
        self.test = test
        self.if_node = if_node
        self.else_node = else_node
        self.cond_name = cond_name
        assert isinstance(test, AstNode)
        assert isinstance(if_node, AstNode)
        assert isinstance(else_node, AstNode)
        assert cond_name is None or type(cond_name) is str

    def __repr__(self):
        return "if {} then {} else {}".format(repr(self.test), repr(self.if_node), repr(self.else_node))

    def append(self, node):
        if node is not None:
            if_node = self.if_node.append(node)
            else_node = self.else_node.append(node) if self.else_node is not None else node
            return _cl(AstIf(self.test, if_node, else_node), self)
        else:
            return self

    @property
    def has_elif(self):
        return isinstance(self.else_node, AstIf)

    @property
    def has_else(self):
        if isinstance(self.else_node, AstValue) and self.else_node.value is None:
            return False
        else:
            return True

    @property
    def is_equality_test(self):
        if isinstance(self.test, AstCompare):
            return self.test.op == '==' and self.test.second_op is None
        else:
            return False

    def cond_tuples(self):
        result = []
        current = self
        while isinstance(current, AstIf):
            result.append((current.test, current.if_node))
            current = current.else_node
        if current is not None:
            result.append((AstValue(True), current))
        return result

    @classmethod
    def from_cond_tuples(cls, cond):
        if len(cond) == 0:
            return makeBody([])
        elif len(cond) == 1:
            a, b = cond[0]
            if is_boolean_true(a):
                return b
            else:
                return AstIf(a, b)
        else:
            a, b = cond[0]
            return AstIf(a, b, cls.from_cond_tuples(cond[1:]))


class AstImport(AstNode):

    def __init__(self, module_name:str, imported_names:Optional[list]=None, alias:Optional[str]=None):
        self.module_name = module_name
        self.imported_names = imported_names
        self.alias = alias
        assert type(module_name) is str and module_name != ''
        assert (imported_names is None or
                (type(imported_names) is list and all([type(item) is str for item in imported_names])))
        assert alias is None or (type(alias) is str and alias != '')
        assert alias is None or (imported_names is None or len(imported_names) == 1)

    def __repr__(self):
        alias = "as {}".format(self.alias) if self.alias is not None else ""
        if self.imported_names is None:
            return "import {}{}".format(self.module_name, alias)
        else:
            return "from {} import {}{}".format(self.module_name, ','.join(self.imported_names), alias)


class AstLet(AstNode):

    def __init__(self, target:str, source:AstNode, body:AstNode, original_target:Optional[str]=None):
        self.target = target
        self.source = source
        self.body = body
        self.original_target = target if original_target is None else original_target
        assert type(target) is str
        assert isinstance(source, AstNode)
        assert isinstance(body, AstNode)

    def __repr__(self):
        bindings = '{} := {}'.format(self.target, repr(self.source))
        return "let [{}] in ({})".format(bindings, repr(self.body))

    def append(self, node):
        if node is not None:
            return _cl(AstLet(self.target, self.source, self.body.append(node)), self)
        else:
            return self


class AstListFor(AstNode):

    def __init__(self, target:str, source:AstNode, expr:AstNode, test:Optional[AstNode]=None,
                 original_target:Optional[str]=None):
        self.target = target
        self.source = source
        self.expr = expr
        self.test = test
        self.original_target = target if original_target is None else original_target
        assert type(target) is str
        assert isinstance(source, AstNode)
        assert isinstance(expr, AstNode)
        assert test is None or isinstance(test, AstNode)

    def __repr__(self):
        if self.test is not None:
            return "[{} for {} in {} if {}]".format(repr(self.expr), self.target, repr(self.source), repr(self.test))
        else:
            return "[{} for {} in {}]".format(repr(self.expr), self.target, repr(self.source))


class AstMultiSlice(AstNode):

    def __init__(self, base:AstNode, indices:list):
        self.base = base
        self.indices = indices
        assert isinstance(base, AstNode)
        assert all([index is None or isinstance(index, AstNode) for index in indices])

    def __repr__(self):
        slices = []
        for index in self.indices:
            if index is None:
                slices.append(':')
            else:
                slices.append(repr(index))
        return "{}[{}]".format(repr(self.base), ','.join(slices))


class AstNamespace(AstNode):

    def __init__(self, name: str, bindings: dict):
        self.name = name
        self.bindings = bindings
        assert type(self.name) is str and self.name != ''
        assert type(self.bindings) is dict

    def __getitem__(self, item):
        return self.bindings[item]

    def __repr__(self):
        return "namespace[{}]".format(self.name)


class AstObserve(AstNode):

    def __init__(self, dist:AstNode, value:AstNode):
        self.dist = dist
        self.value = value
        assert isinstance(self.dist, AstNode)
        assert isinstance(self.value, AstNode)

    def __repr__(self):
        return "observe({}, {})".format(repr(self.dist), repr(self.value))



class AstReturn(AstNode):

    def __init__(self, value:AstNode):
        if value is None:
            value = AstValue(None)
        self.value = value
        assert isinstance(self.value, AstNode)

    def __repr__(self):
        return "return {}".format(repr(self.value))

    def append(self, _):
        return self


class AstSample(AstNode):

    def __init__(self, dist: AstNode, size: Optional[AstNode]=None):
        self.dist = dist
        self.size = size
        assert isinstance(dist, AstNode)
        assert size is None or isinstance(size, AstNode)

    def __repr__(self):
        if self.size is None:
            return "sample({})".format(repr(self.dist))
        else:
            return "sample({}, size={})".format(repr(self.dist), repr(self.size))


class AstSlice(AstNode):

    def __init__(self, base:AstNode, start:Optional[AstNode], stop:Optional[AstNode]):
        self.base = base
        self.start = start
        self.stop = stop
        assert isinstance(base, AstNode)
        assert start is None or isinstance(start, AstNode)
        assert stop is None or isinstance(stop, AstNode)

    def __repr__(self):
        return "{}[{}:{}]".format(
            repr(self.base),
            repr(self.start) if self.start is not None else '',
            repr(self.stop) if self.stop is not None else ''
        )

    @property
    def start_as_int(self):
        if isinstance(self.start, AstValue) and type(self.start.value) is int:
            return self.start.value
        else:
            return None

    @property
    def stop_as_int(self):
        if isinstance(self.stop, AstValue) and type(self.stop.value) is int:
            return self.stop.value
        else:
            return None


class AstSubscript(AstNode):

    def __init__(self, base:AstNode, index:AstNode, default:Optional[AstNode]=None):
        self.base = base
        self.index = index
        self.default = default
        if isinstance(index, AstValue):
            self.index_n = int(index.value) if type(index.value) in [int, bool] else None
        else:
            self.index_n = None
        assert isinstance(base, AstNode)
        assert isinstance(index, AstNode)
        assert default is None or isinstance(default, AstNode)

    def __repr__(self):
        if self.default is not None:
            return "{}.get({}, {})".format(repr(self.base), repr(self.index), repr(self.default))
        else:
            return "{}[{}]".format(repr(self.base), repr(self.index))

    @property
    def index_as_int(self):
        if isinstance(self.index, AstValue):
            return self.index.value if type(self.index.value) is int else None
        else:
            return None


class AstSymbol(AstLeaf):

    def __init__(self, name:str, import_source:Optional[str]=None, protected:bool=False, node=None, predef=False,
                 original_name:Optional[str]=None):
        if original_name is None:
            original_name = name
        self.name = name
        self.import_source = import_source
        self.protected = protected
        self.original_name = original_name
        self.symbol = None
        self.node = node
        self.predef = predef
        assert type(name) is str
        assert import_source is None or type(import_source) is str
        assert type(protected) is bool
        assert type(self.predef) is bool

    def __repr__(self):
        return self.name

    def startswith(self, prefix:str):
        return self.name.startswith(prefix)

    def equals(self, node):
        return self.name == node.name

    @property
    def is_readonly(self):
        if self.symbol is not None:
            return self.symbol.modify_count == 0
        else:
            return False

    @property
    def usage_count(self):
        if self.symbol is not None:
            return self.symbol.usage_count
        else:
            return None


class AstUnary(AstOperator):

    __unary_ops = {
        '+':   ('plus',  lambda x: x),
        '-':   ('minus', lambda x: -x),
        'not': ('not',   lambda x: not x),
    }

    def __init__(self, op:str, item:AstNode):
        self.op = op
        self.item = item
        assert op in self.__unary_ops
        assert isinstance(item, AstNode)

    def __repr__(self):
        return "{}{}".format(self.op, repr(self.item))

    def get_visitor_names(self):
        name = 'visit_unary_' + self.op_name
        return [name] + super(AstUnary, self).get_visitor_names()

    @property
    def op_function(self):
        return self.__unary_ops[self.op][1]

    @property
    def op_name(self):
        return self.__unary_ops[self.op][0]


class AstValue(AstLeaf):

    def __init__(self, value):
        self.value = value
        assert value is None or type(value) in [bool, complex, float, int, str]

    def __repr__(self):
        return repr(self.value)

    def equals(self, other):
        return self.value == other.value


class AstValueVector(AstLeaf):

    def __init__(self, items:list):
        self.items = items

        def is_value_vector(v):
            if type(v) in (list, tuple):
                return all([is_value_vector(w) for w in v])
            else:
                return type(v) in [bool, complex, float, int, str]

        assert type(items) is list and is_value_vector(items)

    def __getitem__(self, item):
        return AstValue(self.items[item])

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return (AstValue(item) for item in self.items)

    def __repr__(self):
        return repr(self.items)

    def conj(self, element):
        if type(element) in [bool, complex, float, int, str]:
            return AstValueVector(self.items + [element])
        elif isinstance(element, AstValue):
            return AstValueVector(self.items + [element.value])
        elif isinstance(element, AstNode):
            return AstVector([AstValue(item) for item in self.items] + [element])
        else:
            return AstCall(AstSymbol('conj'), [self, element])

    def cons(self, element):
        if type(element) in [bool, complex, float, int, str]:
            return AstValueVector([element] + self.items)
        elif isinstance(element, AstValue):
            return AstValueVector([element.value] + self.items)
        elif isinstance(element, AstNode):
            return AstVector([AstValue(element)] + [AstValue(item) for item in self.items])
        else:
            return AstCall(AstSymbol('cons'), [element, self])

    def equals(self, other):
        return all([i == j for i, j in zip(self.items, other.items)])

    def to_vector(self):
        return AstVector([AstValue(item) for item in self.items])

    @property
    def is_empty(self):
        return len(self.items) == 0

    @property
    def non_empty(self):
        return len(self.items) != 0

    @property
    def value(self):
        return self.items


class AstVector(AstNode):

    def __init__(self, items:list):
        self.items = items
        assert type(items) is list and all([isinstance(item, AstNode) for item in items])

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __repr__(self):
        return "[{}]".format(', '.join([repr(item) for item in self.items]))

    def conj(self, element):
        if isinstance(element, AstNode):
            return AstVector(self.items + [element])
        elif type(element) in [bool, complex, float, int, str]:
            return AstVector(self.items + [AstValue(element)])
        else:
            return AstCall(AstSymbol('conj'), [self, element])

    def cons(self, element):
        if isinstance(element, AstNode):
            return AstVector([element] + self.items)
        elif type(element) in [bool, complex, float, int, str]:
            return AstVector([AstValue(element)] + self.items)
        else:
            return AstCall(AstSymbol('cons'), [element, self])

    @property
    def is_empty(self):
        return len(self.items) == 0

    @property
    def non_empty(self):
        return len(self.items) != 0


class AstWhile(AstControl):

    def __init__(self, test:AstCompare, body:AstNode):
        self.test = test
        self.body = body
        assert isinstance(test, AstCompare)
        assert isinstance(body, AstNode)

    def __repr__(self):
        return "while {} do {}".format(repr(self.test), repr(self.body))


#######################################################################################################################

_temp_var_counter = 1000

def generate_cond_var():
    global _temp_var_counter
    _temp_var_counter += 1
    return "__cond_{}__".format(_temp_var_counter)

def generate_temp_var():
    global _temp_var_counter
    _temp_var_counter += 1
    return "__tmp_{}__".format(_temp_var_counter)


def makeBody(*items):
    b_items = []
    for item in items:
        if isinstance(item, AstBody):
            b_items += item.items
        elif isinstance(item, AstNode):
            b_items.append(item)
        elif type(item) in (list, tuple):
            b_items += list(item)
        else:
            raise TypeError("item of type '{}' cannot be part of the AST".format(type(item)))
    items = b_items

    i = 0
    while i < len(items):
        node = items[i]
        if isinstance(node, AstBody):
            del items[i]
            for itm in reversed(node.items):
                items.insert(i, itm)

        elif i+1 == len(items):
            i += 1

        elif isinstance(node, AstBreak) or isinstance(node, AstReturn):
            items = items[:i]
            break

        elif isinstance(node, AstAttribute):
            items[i] = node.base

        elif isinstance(node, AstBinary):
            items[i] = node.right
            items.insert(i, node.left)

        elif isinstance(node, AstCompare):
            items[i] = node.right
            items.insert(i, node.left)
            if node.second_right is not None:
                items.insert(i + 1, node.second_right)

        elif isinstance(node, AstSlice):
            parts = [x for x in (node.stop, node.start, node.base) if x is not None]
            del items[i]
            for p in parts:
                items.insert(i, p)

        elif isinstance(node, AstSubscript):
            items[i] = node.base
            if node.default is not None:
                items.insert(i + 1, node.default)
            items.insert(i + 1, node.index)

        elif isinstance(node, AstSymbol):
            del items[i]

        elif isinstance(node, AstUnary):
            items[i] = node.item

        elif isinstance(node, AstValue) or isinstance(node, AstValueVector):
            del items[i]

        elif isinstance(node, AstVector):
            del items[i]
            for itm in reversed(node.items):
                items.insert(i, itm)

        else:
            i += 1

    if len(items) == 1:
        return items[0]

    else:
        return AstBody(items)


def makeDef(target, value:AstNode, is_global:bool=False):
    if type(target) is str:
        return AstDef(target, value, global_context=is_global)

    elif type(target) is tuple and all(type(t) is str for t in target):
        tmp = generate_temp_var()
        result = [AstDef(tmp, value, is_global)]
        i = 0
        while i < len(target):
            if target[i] != '_':
                result.append(AstDef(target[i], makeSubscript(tmp, i), is_global))
            i += 1
        return makeBody(result)
    else:
        raise TypeError("cannot create 'def' for target '{}'".format(target))


def makeFor(target, source, body):
    if type(target) is tuple:
        tmp = generate_temp_var()
        i = len(target)
        while i > 0:
            i -= 0
            body = AstLet(target[i], makeSubscript(tmp, i), body)
        target = tmp
    return AstFor(target, source, body)


def makeIf(test, if_node, else_node):
    if is_empty(if_node) and is_empty(else_node):
        return test

    elif is_empty(if_node):
        test = AstUnary('not', test)
        if_node, else_node = else_node, if_node

    if if_node is None:
        if_node = AstValue(None)
    if else_node is None:
        else_node = AstValue(None)

    if is_unary_not(test) and is_boolean(test.item):
        test = AstValue(not test.item.value)

    if is_boolean(test):
        if test.value:
            return if_node
        else:
            return else_node

    if isinstance(if_node, AstDef) and isinstance(else_node, AstDef):
        if if_node.name == else_node.name:
            return AstDef(if_node.name, makeIf(test, if_node.value, else_node.value))

    if isinstance(test, AstSymbol) or isinstance(test, AstValue) or \
            (is_unary_not(test) and isinstance(test.item, AstSymbol)):
        return AstIf(test, if_node, else_node)
    else:
        return AstIf(test, if_node, else_node)


def makeLet(targets:list, sources:list, body:AstNode, original_target:Optional[str]=None):
    if type(targets) in (str, tuple):
        targets = [targets]
        sources = [sources]
    assert len(targets) == len(sources) > 0
    if len(targets) == 1:
        target = targets[0]
        if target == '_':
            return makeBody(sources, body)

        elif type(target) is tuple:
            tmp = generate_temp_var()
            i = len(target)
            while i > 0:
                i -= 0
                body = AstLet(target[i], makeSubscript(tmp, i), body)
            return AstLet(tmp, sources[0], body)

        return AstLet(targets[0], sources[0], body, original_target=original_target)

    else:
        return makeLet(targets[:-1], sources[:-1], AstLet(targets[-1], sources[-1], body))


def makeListFor(target, source, expr, test=None):
    if type(target) is tuple:
        tmp = generate_temp_var()
        i = len(target)
        while i > 0:
            i -= 1
            expr = AstLet(target[i], makeSubscript(tmp, i), expr)
        target = tmp
    return AstListFor(target, source, expr, test)


def makeSubscript(base, index, default=None):
    if type(index) is int:
        index = AstValue(index)
    if type(base) is str:
        base = AstSymbol(base)

    if is_vector(base) and is_integer(index):
        i = index.value
        if 0 <= i < len(base.items):
            return base[i]
        elif -len(base.items) <= i < 0:
            return base[i]

    elif isinstance(base, AstDict) and isinstance(index, AstValue):
        result = base.items.get(index.value, default)
        if result is not None:
            return result

    return AstSubscript(base, index, default)


def makeVector(items):
    if all([isinstance(item, AstValue) for item in items]):
        return AstValueVector([item.value for item in items])
    elif all([type(item) in [bool, complex, float, int, str] for item in items]):
        return AstValueVector(items)
    else:
        return AstVector(items)


#######################################################################################################################

def has_return(node:AstNode):
    if isinstance(node, AstReturn):
        return True
    elif isinstance(node, AstBody):
        return has_return(node[-1]) if len(node) > 0 else False
    else:
        return False

def is_binary_add_sub(node:AstNode):
    if isinstance(node, AstBinary):
        return node.op in ['+', '-']
    else:
        return False

def is_boolean(node:AstNode):
    if isinstance(node, AstValue):
        return type(node.value) is bool
    else:
        return False

def is_boolean_true(node:AstNode):
    if isinstance(node, AstValue):
        return node.value is True
    else:
        return False

def is_call(node:AstNode, name:Optional[str]=None):
    if isinstance(node, AstCall):
        return (name is None) or (node.function_name == name)
    else:
        return False

def is_constant(node:AstNode):
    return isinstance(node, AstValue) or isinstance(node, AstValueVector)

def is_empty(node:AstNode):
    if node is None:
        return True
    elif isinstance(node, AstBody):
        return node.is_empty
    elif isinstance(node, AstValueVector) or isinstance(node, AstVector):
        return node.is_empty
    elif isinstance(node, AstValue):
        return node.value is None
    else:
        return False

def is_function(node:AstNode, name:Optional[str]=None):
    if isinstance(node, AstFunction):
        return (name is None) or node.function_name == name
    else:
        return False

def is_integer(node:AstNode):
    if isinstance(node, AstValue):
        return type(node.value) is int
    else:
        return False

def is_negation_of(nodeA:AstNode, nodeB:AstNode):
    if isinstance(nodeA, AstUnary):
        if nodeA.op == 'not' and nodeA.item == nodeB:
            return True
    if isinstance(nodeB, AstUnary):
        if nodeB.op == 'not' and nodeB.item == nodeA:
            return True
    if is_boolean(nodeA) and is_boolean(nodeB):
        return nodeA.value != nodeB.value
    return False

def is_none(node:AstNode):
    if isinstance(node, AstValue):
        return node.value is None
    else:
        return False

def is_non_empty_body(node:AstNode):
    if isinstance(node, AstBody):
        return len(node) > 0
    else:
        return False

def is_number(node:AstNode):
    if isinstance(node, AstValue):
        return type(node.value) in [complex, float, int]
    else:
        return False

def is_string(node:AstNode):
    if isinstance(node, AstValue):
        return type(node.value) is str
    else:
        return False

def is_symbol(node:AstNode, symbol:Optional[str]=None):
    if isinstance(node, AstSymbol):
        return symbol is None or node.name == symbol
    else:
        return False

def is_unary_neg(node:AstNode):
    if isinstance(node, AstUnary):
        return node.op == '-'
    else:
        return False

def is_unary_not(node:AstNode):
    if isinstance(node, AstUnary):
        return node.op == 'not'
    else:
        return False

def is_value(node:AstNode):
    return isinstance(node, AstValue) or isinstance(node, AstValueVector)

def is_vector(node:AstNode):
    return isinstance(node, AstValueVector) or isinstance(node, AstVector)

def is_zero(node: AstNode):
    if isinstance(node, AstValue):
        return node.value == 0
    else:
        return False
