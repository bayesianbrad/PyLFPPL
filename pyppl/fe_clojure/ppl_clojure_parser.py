#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Feb 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
from ..fe_clojure import ppl_clojure_forms as clj
from ..ppl_ast import *
from .ppl_clojure_lexer import ClojureLexer


#######################################################################################################################

class ClojureParser(clj.Visitor):

    __core_functions__ = {
        'append',
        'concat',
        'conj',
        'cons',
        'filter',
        'interleave',
        'into',
        'map',
        'prepend',
        'reduce',
    }

    def parse_alias(self, alias):
        if clj.is_quoted(alias):
            alias = alias.last
            if clj.is_symbol(alias):
                return alias.name, None

            elif clj.is_form(alias) and len(alias) == 1 and clj.is_symbol(alias.head):
                return alias.head.name, None

            elif clj.is_symbol_vector(alias) and len(alias) == 3 and clj.is_symbol(alias[1], ':as'):
                return alias.head.name, alias.last.name

        return None, None

    def parse_bindings(self, bindings):
        if clj.is_vector(bindings):
            if len(bindings) % 2 != 0:
                raise TypeError("the bindings must contain an even number of elements: '{}'".format(bindings))
            targets = bindings.items[0::2]
            values = bindings.items[1::2]
            names = [self.parse_target(target) for target in targets]
            values = [value.visit(self) for value in values]
            return names, values

        else:
            raise TypeError("the bindings must be a vector instead of '{}'".format(bindings))

    def parse_body(self, body, *, use_return:bool=False):
        body = [item.visit(self) for item in body]
        if use_return:
            if len(body) > 0:
                body[-1] = AstReturn(body[-1])
            else:
                body.append(AstReturn(AstValue(None)))
        if len(body) == 1:
            return body[0]
        else:
            return makeBody(body)

    def parse_function(self, parameters, body):
        if clj.is_symbol_vector(parameters):
            params = [p.name for p in parameters.items]
            if len(params) >= 2 and params[-2] == '&':
                vararg = params[-1]
                params = params[:-2]
            else:
                vararg = None
            if '&' in params:
                raise SyntaxError("invalid parameters: '{}'".format(parameters))
        else:
            raise TypeError("invalid function parameters: '{}'".format(parameters))
        body = self.parse_body(body, use_return=True)
        return params, vararg, body

    def parse_target(self, target):
        if clj.is_symbol(target):
            target = target.name
        elif clj.is_symbol_vector(target):
            target = tuple([t.name for t in target.items])
        else:
            raise TypeError("invalid target in assignment: '{}'".format(target))
        return target

    def visit_apply(self, function, *args):
        function = function.visit(self)
        args = [arg.visit(self) for arg in args]
        return AstCall(function, args)

    def visit_concat(self, *seqs):
        seqs = [s.visit(self) for s in seqs]
        if len(seqs) == 0:
            return AstValue(None)
        elif len(seqs) == 1:
            return seqs[0]
        else:
            return AstCall(AstSymbol('clojure.core.concat'), seqs)

    def visit_cond(self, *clauses):
        if len(clauses) == 0:
            return makeBody([])
        if len(clauses) % 2 != 0:
            raise SyntaxError("the number of clauses in 'cond' must be even")
        clauses = list(reversed(clauses))
        result = clauses[0].visit(self)
        if not clj.is_symbol(clauses[1], ':else'):
            result = makeIf(clauses[1].visit(self), result, None)
        for test, body in zip(clauses[3::2], clauses[2::2]):
            result = makeIf(test.visit(self), body.visit(self), result)
        return result

    def visit_conj(self, sequence, *elements):
        sequence = sequence.visit(self)
        elements = [e.visit(self) for e in elements]
        result = sequence
        for element in elements:
            result = AstCall(AstSymbol('clojure.core.conj'), [result, element])
        return result

    def visit_cons(self, element, sequence):
        element = element.visit(self)
        sequence = sequence.visit(self)
        return AstCall(AstSymbol('clojure.core.cons'), [element, sequence])

    def visit_dec(self, number):
        return AstBinary(number.visit(self), '-', AstValue(1))

    def visit_def(self, target, source):
        target = self.parse_target(target)
        source = source.visit(self)
        return makeDef(target, source, True)

    def visit_defn(self, name, parameters, *body):
        if clj.is_symbol(name):
            name = name.name
        else:
            raise TypeError("function name expected instead of '{}'".format(name))
        if clj.is_string(parameters) and len(body) > 1 and clj.is_symbol_vector(body[0]):
            doc_string, parameters = parameters, body[0]
            body = body[1:]
        else:
            doc_string = None
        params, vararg, body = self.parse_function(parameters, body)
        return makeDef(name, AstFunction(name, params, body, vararg=vararg, doc_string=doc_string), True)

    def visit_do(self, body):
        return self.parse_body(body)

    def visit_doseq(self, bindings, *body):
        targets, sources = self.parse_bindings(bindings)
        result = self.parse_body(body)
        for target, source in zip(reversed(targets), reversed(sources)):
            result = makeFor(target, source, result)
        return result

    def visit_drop(self, count, sequence):
        count = count.visit(self)
        sequence = sequence.visit(self)
        return AstSlice(sequence, count, None)

    def visit_first(self, sequence):
        sequence = sequence.visit(self)
        return AstSubscript(sequence, AstValue(0))

    def visit_fn(self, parameters, *body):
        params, vararg, body = self.parse_function(parameters, body)
        return AstFunction(None, params, body, vararg=vararg)

    def visit_for(self, bindings, *body):
        targets, sources = self.parse_bindings(bindings)
        result = self.parse_body(body)
        for target, source in zip(reversed(targets), reversed(sources)):
            result = makeListFor(target, source, result)
        return result

    def visit_get(self, sequence, index, *defaults):
        sequence = sequence.visit(self)
        index = index.visit(self)
        if len(defaults) == 0:
            default = None
        elif len(defaults) == 1:
            default = defaults[0]
        else:
            raise TypeError("too many arguments for 'get' ({} given)".format(len(defaults) + 2))

        if isinstance(sequence, AstSlice) and sequence.stop is None and is_integer(index) and default is None:
            start = sequence.start_as_int
            if start is not None:
                return AstSubscript(sequence.base, AstValue(start + index.value))
        return AstSubscript(sequence, index, default)

    def visit_if(self, test, body, *else_body):
        if len(else_body) > 1:
            raise SyntaxError("too many arguments for 'if' ({} given)".format(len(else_body) + 2))
        test = test.visit(self)
        body = body.visit(self)
        else_body = else_body[0].visit(self) if len(else_body) == 1 else None
        return makeIf(test, body, else_body)

    def visit_if_not(self, test, body, *else_body):
        if len(else_body) == 1:
            return self.visit_if(test, else_body[0], body)
        elif len(else_body) == 0:
            return self.visit_if(clj.Form([clj.Symbol('not'), test]), body, else_body[0])
        else:
            raise SyntaxError("too many arguments for 'if-not' ({} given)".format(len(else_body)+2))

    def visit_inc(self, number):
        return AstBinary(number.visit(self), '+', AstValue(1))

    def visit_last(self, sequence):
        sequence = sequence.visit(self)
        return AstSubscript(sequence, AstValue(-1))

    def visit_let(self, bindings, *body):
        targets, sources = self.parse_bindings(bindings)
        return makeLet(targets, sources, self.parse_body(body))

    def visit_nth(self, sequence, index):
        sequence = self.visit(sequence)
        index = self.visit(index)
        if isinstance(sequence, AstSlice) and sequence.stop is None and is_integer(index):
            start = sequence.start_as_int
            if start is not None:
                return AstSubscript(sequence.base, AstValue(start + index.value))
        return AstSubscript(sequence, index)

    def visit_observe(self, dist, value):
        return AstObserve(dist.visit(self), value.visit(self))

    def visit_put(self, sequence, index, value):
        sequence = self.visit(sequence)
        index = self.visit(index)
        value = self.visit(value)
        return AstCall(AstSymbol('list.put'), [sequence, index, value], is_builtin=True)

    def visit_repeat(self, count, value):
        value = value.visit(self)
        if clj.is_integer(count):
            n = count.value
            return makeVector([value] * n)
        else:
            count = count.visit(self)
            return AstBinary(AstVector([value]), '*', count)

    def visit_repeatedly(self, count, function):
        function = function.visit(self)
        if clj.is_integer(count):
            n = count.value
            return makeVector([AstCall(function, [])] * n)
        else:
            count = count.visit(self)
            return AstBinary(AstVector([AstCall(function, [])]), '*', count)

    def visit_require(self, *args):
        result = []
        for arg in args:
            name, as_name = self.parse_alias(arg)
            if name is None:
                raise SyntaxError("cannot import '{}'".format(arg))
            result.append(AstImport(name, [], as_name))

        if len(result) == 1:
            return result[0]
        else:
            return makeBody(result)

    def visit_rest(self, sequence):
        sequence = sequence.visit(self)
        if isinstance(sequence, AstSlice):
            start = sequence.start_as_int
            if start is not None:
                return AstSlice(sequence.base, AstValue(start + 1), sequence.stop)
        return AstSlice(sequence, AstValue(1), None)

    def visit_sample(self, dist, *size):
        if len(size) == 1:
            size = self.visit(size[0])
        else:
            if len(size) > 0:
                raise TypeError("sample() expected 1 or 2 arguments ({} given)".format(len(size)+1))
            size = None
        return AstSample(self.visit(dist), size=size)

    def visit_second(self, sequence):
        sequence = sequence.visit(self)
        return AstSubscript(sequence, AstValue(1))

    def visit_setv(self, target, source):
        target = self.parse_target(target)
        source = source.visit(self)
        return AstDef(target, source)

    def visit_subvec(self, sequence, start, *stop):
        if len(stop) > 1:
            raise TypeError("subvec() takes at most three arguments ({} given)".format(len(stop) + 2))
        sequence = sequence.visit(self)
        start = start.visit(self)
        stop = stop[0].visit(self) if len(stop) > 0 else None
        return AstSlice(sequence, start, stop)

    def visit_sym_arrow(self, init_arg, *functions):
        result = init_arg
        for arg in functions:
            if clj.is_form(arg):
                result = clj.Form([arg.head, result] + arg.tail)
            else:
                result = clj.Form([arg, result])
        return result.visit(self)

    def visit_sym_double_arrow(self, init_arg, *functions):
        result = init_arg
        for arg in functions:
            if clj.is_form(arg):
                result = clj.Form(arg.items + [result])
            else:
                result = clj.Form([arg, result])
        return result.visit(self)

    def visit_take(self, count, sequence):
        count = count.visit(self)
        sequence = sequence.visit(self)
        return AstSlice(sequence, None, count)

    def visit_use(self, *args):
        result = []
        for arg in args:
            name, as_name = self.parse_alias(arg)
            if name is None:
                raise SyntaxError("cannot import '{}'".format(arg))
            result.append(AstImport(name, ['*']))

        if len(result) == 1:
            return result[0]
        else:
            return makeBody(result)

    def visit_vector(self, *items):
        items = [item.visit(self) for item in items]
        return makeVector(items)

    def visit_while(self, test, *body):
        test = test.visit(self)
        body = self.parse_body(body)
        return AstWhile(test, body)

    ###

    def visit_form_form(self, node:clj.Form):
        function = node.head.visit(self)
        args = [item.visit(self) for item in node.tail]
        if isinstance(function, AstSymbol):
            n = function.name
            if n in ['+', '-', 'not'] and len(args) == 1:
                return AstUnary(n, args[0])

            elif n in ['+', '-', '*', '/', 'and', 'or', 'bit-and', 'bit-or', 'bit-xor']:
                if n == 'bit-and': n = '&'
                if n == 'bit-or': n = '|'
                if n == 'bit-xor': n = '^'
                if len(args) == 0:
                    return AstValue(0 if n in ['+', '-'] else 1)
                result = args[0]
                for arg in args[1:]:
                    result = AstBinary(result, n, arg)
                return result

            elif n in ['<', '>', '<=', '>=', '=', '!=', '==', 'not=']:
                if n == 'not=': n = '!='
                if n == '=': n = '=='
                if len(args) != 2:
                    raise TypeError("comparison requires exactly two arguments ({} given)".format(len(args)))
                return AstCompare(args[0], n, args[1])

            elif n == '.':
                if len(args) < 2:
                    raise TypeError("attribute access requires at least two arguments ({} given)".format(len(args)))
                result = args[0]
                for arg in args[1:]:
                    if isinstance(arg, AstSymbol):
                        result = AstAttribute(result, arg.name)
                    else:
                        raise TypeError("attribute access: fields must be names instead of '{}'".format(arg))
                return result

            elif n == 'contains?':
                if len(args) != 2:
                    raise TypeError("comparison requires exactly two arguments ({} given)".format(len(args)))
                return AstCompare(args[1], 'in', args[0])

            elif n.startswith(':') and len(args) == 1:
                return AstSubscript(args[0], AstValue(n[1:]))

            elif n in self.__core_functions__:
                return AstCall(AstSymbol('clojure.core.' + n, predef=True), args)

        return AstCall(function, args)

    def visit_map_form(self, node:clj.Map):
        keys = [key.visit(self) for key in node.items[0::2]]
        values = [value.visit(self) for value in node.items[1::2]]
        items = {}
        for key, value in zip(keys, values):
            if isinstance(key, AstSymbol) and key.startswith(':'):
                items[key.name[1:]] = value
            elif isinstance(key, AstValue):
                items[key.value] = value
            else:
                raise SyntaxError("invalid key for map: '{}'".format(key))
        return AstDict(items)

    def visit_symbol_form(self, node:clj.Symbol):
        return AstSymbol(node.name)

    def visit_value_form(self, node:clj.Value):
        return AstValue(node.value)

    def visit_vector_form(self, node:clj.Vector):
        items = [item.visit(self) for item in node.items]
        return makeVector(items)


#######################################################################################################################

def parse(source):
    clj_ast = list(ClojureLexer(source))
    ppl_ast = ClojureParser().visit(clj_ast)
    return ppl_ast
