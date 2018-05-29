#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Feb 2018, Tobias Kohn
# 28. Feb 2018, Tobias Kohn
#
from typing import Optional
import inspect
from ast import copy_location

class ClojureObject(object):

    _attributes = {'col_offset', 'lineno'}
    tag = None

    def visit(self, visitor):
        """
        The visitor-object given as argument must provide at least one `visit_XXX`-method to be called by this method.
        If the visitor does not provide any specific `visit_XXX`-method to be called, the method will try and call
        `visit_node` or `generic_visit`, respectively.

        :param visitor: An object with a `visit_XXX`-method.
        :return:        The result returned by the `visit_XXX`-method of the visitor.
        """
        name = self.__class__.__name__.lower()
        method_names = ['visit_' + name + '_form', 'visit_node', 'generic_visit']
        methods = [getattr(visitor, name, None) for name in method_names]
        methods = [name for name in methods if name is not None]
        if len(methods) == 0 and callable(visitor):
            return visitor(self)
        elif len(methods) > 0:
            result = methods[0](self)
            if hasattr(result, '_attributes'):
                result = copy_location(result, self)
            return result
        else:
            raise RuntimeError("visitor '{}' has no visit-methods to call".format(type(visitor)))


#######################################################################################################################

class Form(ClojureObject):

    def __init__(self, items:list, lineno:Optional[int]=None):
        self.items = items
        if lineno is not None:
            self.lineno = lineno
        self._special_names = {
            '->':  'arrow',
            '->>': 'double_arrow',
            '.':   'dot'
        }
        assert type(items) in [list, tuple]
        assert all([isinstance(item, ClojureObject) for item in items])
        assert lineno is None or type(lineno) is int

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        return "({})".format(' '.join([repr(item) for item in self.items]))

    def visit(self, visitor):
        name = self.name
        if name is not None:
            if name in self._special_names:
                name = '_sym_' + self._special_names[name]
            if name.endswith('?'):
                name = 'is_' + name[:-1]
            name = name.replace('-', '_').replace('.', '_').replace('/', '_')
            name = ''.join([n if n.islower() else "_" + n.lower() for n in name])
            method = getattr(visitor, 'visit_' + name, None)
            if method is not None:
                arg_count = len(self.items) - 1
                has_varargs = inspect.getfullargspec(method).varargs is not None
                param_count = len(inspect.getfullargspec(method).args) - 1
                has_correct_arg_count = arg_count >= param_count if has_varargs else arg_count == param_count
                if not has_correct_arg_count:
                    s = "at least" if has_varargs else "exactly"
                    if param_count == 0:
                        t = "no arguments"
                    elif param_count == 1:
                        t = "one argument"
                    elif param_count == 2:
                        t = "two arguments"
                    elif param_count == 3:
                        t = "three arguments"
                    else:
                        t = "{} arguments".format(param_count)
                    pos = "(line {})".format(self.lineno) if self.lineno is not None else ''
                    raise TypeError("{}() takes {} {} ({} given) {}".format(self.name, s, t, arg_count, pos))

                result = method(*self.items[1:])
                if hasattr(result, '_attributes'):
                    result = copy_location(result, self)
                return result

        return super(Form, self).visit(visitor)

    @property
    def head(self):
        return self.items[0]

    @property
    def tail(self):
        return Form(self.items[1:])

    @property
    def last(self):
        return self.items[-1]

    @property
    def name(self):
        if len(self.items) > 0 and isinstance(self.items[0], Symbol):
            return self.items[0].name
        else:
            return None

    @property
    def is_empty(self):
        return len(self.items) == 0

    @property
    def non_empty(self):
        return len(self.items) > 0

    @property
    def length(self):
        return len(self.items)


class Map(ClojureObject):

    def __init__(self, items:list, lineno:Optional[int]=None):
        self.items = items
        assert type(items) is list
        assert all([isinstance(item, ClojureObject) for item in items])
        assert len(self.items) % 2 == 0
        assert lineno is None or type(lineno) is int

    def __repr__(self):
        return "{" + ' '.join([repr(item) for item in self.items]) + "}"



class Symbol(ClojureObject):

    def __init__(self, name:str, lineno:Optional[int]=None):
        self.name = name
        if lineno is not None:
            self.lineno = lineno
        assert type(name) is str
        assert lineno is None or type(lineno) is int

    def __repr__(self):
        return self.name


class Value(ClojureObject):

    def __init__(self, value, lineno:Optional[int]=None):
        self.value = value
        if lineno is not None:
            self.lineno = lineno
        assert value is None or type(value) in [bool, complex, float, int, str]
        assert lineno is None or type(lineno) is int

    def __repr__(self):
        return repr(self.value)


class Vector(ClojureObject):

    def __init__(self, items:list, lineno:Optional[int]=None):
        self.items = items
        if lineno is not None:
            self.lineno = lineno
        assert type(items) in [list, tuple]
        assert all([isinstance(item, ClojureObject) for item in items])
        assert lineno is None or type(lineno) is int

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        return "[{}]".format(' '.join([repr(item) for item in self.items]))

    @property
    def is_empty(self):
        return len(self.items) == 0

    @property
    def non_empty(self):
        return len(self.items) > 0

    @property
    def length(self):
        return len(self.items)

#######################################################################################################################

class Visitor(object):

    def visit(self, ast):
        if isinstance(ast, ClojureObject):
            return ast.visit(self)
        elif hasattr(ast, '__iter__'):
            return [self.visit(item) for item in ast]
        else:
            raise TypeError("cannot walk/visit an object of type '{}'".format(type(ast)))

    def visit_node(self, node:ClojureObject):
        return node


class LeafVisitor(Visitor):

    def visit_symbol(self, node:Symbol):
        self.visit_node(node)

    def visit_value(self, node:Value):
        self.visit_node(node)

    def visit_form_form(self, node:Form):
        for n in node.items:
            n.visit(self)

    def visit_map_form(self, node:Map):
        for n in node.items:
            n.visit(self)

    def visit_symbol_form(self, node:Symbol):
        self.visit_symbol(node)

    def visit_value_form(self, node:Value):
        self.visit_value(node)

    def visit_vector_form(self, node:Vector):
        for n in node.items:
            n.visit(self)


#######################################################################################################################

def is_form(form):
    return isinstance(form, Form)

def is_integer(form):
    if isinstance(form, Value):
        return type(form.value) is int
    else:
        return False

def is_map(form):
    return isinstance(form, Map)

def is_numeric(form):
    if isinstance(form, Value):
        return type(form.value) in [complex, float, int]
    else:
        return False

def is_quoted(form):
    return isinstance(form, Form) and len(form) == 2 and is_symbol(form.items[0], 'quote')

def is_string(form):
    if isinstance(form, Value):
        return type(form.value) is str
    else:
        return False

def is_symbol(form, symbol:str=None):
    if isinstance(form, Symbol):
        return form.name == symbol if symbol is not None else True
    else:
        return False

def is_symbol_vector(form):
    if isinstance(form, Vector):
        return all([isinstance(item, Symbol) for item in form.items])
    else:
        return False

def is_vector(form):
    return isinstance(form, Vector)
