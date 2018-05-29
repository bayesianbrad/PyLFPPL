#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 21. Dec 2017, Tobias Kohn
# 31. Jan 2018, Tobias Kohn
#
from .foppl_ast import *
from .foppl_reader import *
from .distributions import distributions_map
from . import Options

def _register(name):
    def _name_(cls):
        cls.name = name
        return cls
    return _name_


def get_name(obj):
    if isinstance(obj, Symbol):
        return obj.name
    if type(obj) is str:
        return obj
    raise RuntimeError("Is not a name '{}'".format(obj))


class ExprParser(object):

    def __init__(self):
        self.parent = None

    def _parse(self, form):
        return self.parent.parse(form)

    def begin_scope(self, scope):
        return self.parent.begin_scope(scope)

    def end_scope(self):
        return self.parent.end_scope()

    def parse(self, form: Form):
        f = form.head

        if f in [Symbol.PLUS, Symbol.MINUS, Symbol.NOT] and len(form) == 2:
            return AstUnary(f, self._parse(form[1]))

        elif f in [Symbol.PLUS, Symbol.MINUS, Symbol.MULTIPLY, Symbol.DIVIDE, Symbol.AND, Symbol.OR, Symbol.XOR]:
            items = [self._parse(item) for item in form.tail]
            result = items[0]
            for item in items[1:]:
                result = AstBinary(f, result, item)
            return result

        elif f in [Symbol.EQ, Symbol.LT, Symbol.LE, Symbol.GT, Symbol.GE]:
            if len(form) != 3:
                raise SyntaxError("Too many or too few arguments for comparison '{}'".format(repr(f)))
            left = self._parse(form[1])
            right = self._parse(form[2])

            if Options.uniform_conditionals:
                # We convert all comparisons (except for equality) to the pattern `X >= 0`
                if f == Symbol.LE:
                    f = Symbol.GE
                    left, right = right, left

                elif f in [Symbol.GT, Symbol.LT]:
                    if f == Symbol.GT:
                        left, right = right, left
                    if not (isinstance(right, AstValue) and right.value == 0):
                        left = AstBinary('-', left, right)
                        right = AstValue(0)
                    return AstUnary('not', AstCompare(Symbol.GE, left, right))

            if not (isinstance(right, AstValue) and right.value == 0):
                left = AstBinary('-', left, right)
                right = AstValue(0)
            return AstCompare(f, left, right)

        elif isinstance(f, Symbol):
            args = [self._parse(arg) for arg in form.tail]
            if f.name == "sample":
                if len(args) != 1:
                    raise SyntaxError("'sample' requires exactly one argument")
                return AstSample(args[0], line_number=form.line_number)

            elif f.name == "observe":
                if len(args) != 2:
                    raise SyntaxError("'observe' requires exactly two arguments")
                return AstObserve(args[0], args[1], line_number=form.line_number)

            elif f.name == "vector":
                return self._parse(Vector(form.data[1:]))

            elif f.name in ["first", "second", "last"]:
                if len(args) == 1:
                    if f.name == "first":
                        args.append(AstValue(0))
                    elif f.name == "second":
                        args.append(AstValue(1))
                    elif f.name == "last":
                        args.append(AstValue(-1))
                    return AstFunctionCall("get", args)
                else:
                    raise SyntaxError("'{}' expects exactly one argument".format(f.name))

            elif f.name == "nth":
                return AstFunctionCall("get", args)

            elif f.name == "apply":
                return AstFunctionCall(self._parse(form[1]), self._parse(form[2:]))

            elif f.name in distributions_map:
                return AstDistribution(distributions_map[f.name], args, line_number=form.line_number)

            else:
                return AstFunctionCall(f.name, args)

        if type(f) is Form and len(form) == 1:
            return self._parse(f)

        elif type(f) is Form:
            raise SyntaxError("There might be too many parentheses here: '{}'".format(form))

        else:
            raise NotImplementedError(form)

    def resolve_symbol(self, symbol):
        return None


class FunctionParser(ExprParser):

    def _parse_bindings(self, bindings):
        if len(bindings) % 2 != 0 or not isinstance(bindings, Vector):
            raise SyntaxError('let bindings must be a vector with an even number of elements')
        names = []
        assignments = []
        i = 0
        while i < len(bindings):
            name = bindings[i]  # get_name(bindings[i])
            source = bindings[i + 1]
            if isinstance(name, Vector):
                part_names = [get_name(n) for n in name.data]
                overall_name = '_'.join(part_names)
                overall_name = "__" + overall_name
                names.append(overall_name)
                assignments.append((overall_name, self._parse(source)))
                overall_name = AstSymbol(overall_name)
                for j in range(len(part_names)):
                    names.append(part_names[j])
                    assignments.append((part_names[j], AstFunctionCall('get', [overall_name, AstValue(j)])))
            else:
                names.append(get_name(name))
                assignments.append((name, self._parse(source)))
            i += 2
        return names, assignments

    def _parse_params(self, params):
        return params # [get_name(obj) for obj in params]

    def _parse_body(self, params, body):
        body = [self._parse(item) for item in body]
        if len(body) == 1:
            body = body[0]
        else:
            body = AstBody(body)
        return body

    def _parse_function(self, name, params, body):
        params = self._parse_params(params)
        body = self._parse_body(params, body)
        return AstFunction(name, params, body)


class Parser(object):

    @_register(Symbol.DEF)
    class DefExpr(ExprParser):

        def parse(self, form: Form):
            if len(form) != 3 or type(form[1]) is not Symbol:
                raise SyntaxError('def requires a name and a value')
            name = str(form[1])
            source = self._parse(form[2])
            return AstDef(name, source)

    @_register(Symbol.DEFN)
    class DefnExpr(FunctionParser):

        def parse(self, form: Form):
            name = str(form[1])
            function = self._parse_function(name, form[2], form[3:])
            return AstDef(name, function)

    @_register(Symbol.DO)
    class DoExpr(ExprParser):

        def parse(self, form: Form):
            items = [self._parse(f) for f in form.tail]
            return AstBody(items)

    @_register(Symbol.FN)
    class FnExpr(FunctionParser):

        def parse(self, form: Form):
            return self._parse_function('<lambda>', form[1], form[2:])

    @_register(Symbol.FOR)
    class ForExpr(FunctionParser):

        def parse(self, form: Form):
            items = [self._parse(f) for f in form[2:]]
            if len(items) == 1:
                body = items[0]
            else:
                body = AstBody(items)
            if isinstance(form[1], Vector) and len(form[1]) == 2 and isinstance(form[1][0], Vector):
                _, assignments = self._parse_bindings(form[1])
                target, source = assignments[0]
                body = AstLet(assignments[1:], body)
                return AstFor(target, source, body)
            else:
                _, assignments = self._parse_bindings(form[1])
                while len(assignments) > 0:
                    target, source = assignments.pop()
                    body = AstFor(target, source, body)
                return body

    @_register(Symbol.FOR_EACH)
    class ForEachExpr(FunctionParser):

        def parse(self, form: Form):
            items = [self._parse(f) for f in form[2:]]
            if len(items) == 1:
                body = items[0]
            else:
                body = AstBody(items)
            _, assignments = self._parse_bindings(form[1])
            targets = [t for t, _ in assignments]
            sources = [s for _, s in assignments]
            return AstMultiFor(targets, sources, body)

    @_register(Symbol.IF)
    class IfExpr(ExprParser):

        def parse(self, form: Form):
            cond = self._parse(form[1])
            if_body = self._parse(form[2])
            if len(form) == 4:
                else_body = self._parse(form[3])
            else:
                else_body = None
            return AstIf(cond, if_body, else_body, line_number=form.line_number)

    @_register(Symbol.IF_NOT)
    class IfNotExpr(ExprParser):

        def parse(self, form: Form):
            cond = self._parse(form[1])
            if_body = self._parse(form[2])
            if len(form) == 4:
                else_body = if_body
                if_body = self._parse(form[3])
            else:
                else_body = None
                cond = AstUnary(Symbol.NOT, cond)
            return AstIf(cond, if_body, else_body)

    @_register(Symbol.LET)
    class LetExpr(FunctionParser):

        def parse(self, form: Form):
            _, assignments = self._parse_bindings(form[1])
            items = [self._parse(f) for f in form[2:]]
            if len(items) == 1:
                items = items[0]
            else:
                items = AstBody(items)
            return AstLet(assignments, items)

    @_register(Symbol.LOOP)
    class LoopExpr(ExprParser):

        def _parse_step(self, iter_count, function, arg):
            if iter_count == 0:
                pass
            if iter_count > 0:
                AstFunctionCall(function, arg)

        def parse(self, form: Form):
            if len(form) >= 4:
                iter_count = self._parse(form[1])
                #if isinstance(iter_count, AstValue):
                #    iter_count = iter_count.value
                #else:
                #    raise SyntaxError("you must provide a literal value for the number of iterations")
                arg = self._parse(form[2])
                function = self._parse(form[3])
                args = [self._parse(a) for a in form[4:]]
                if not isinstance(function, AstFunction) and not isinstance(function, AstSymbol):
                    raise SyntaxError("the third argument must be a function")

                return AstLoop(iter_count, arg, function, args)
            else:
                raise SyntaxError("loop requires a vector and a function")

    def __init__(self):
        self._parsers = {}
        for d in self.__class__.__dict__:
            if not d.startswith('_'):
                item = self.__class__.__dict__[d]
                if type(item) is type:
                    self._parsers[item.name] = item()
        for p in self._parsers:
            self._parsers[p].parent = self
        self.expr_parser = ExprParser()
        self.expr_parser.parent = self

    def parse(self, form: Form):
        if form is None:
            return AstValue(None)

        form_type = type(form)

        if form_type is Form:
            head = form.head
            if head in self._parsers:
                return self._parsers[head].parse(form)
            return self.expr_parser.parse(form)

        elif form_type in [str, int, float, bool]:
            return AstValue(form)

        elif form_type is Symbol:
            return AstSymbol(form.name)

        elif form_type is Value:
            return AstValue(form.value)

        elif form_type in [Vector]:
            values = [self.parse(item) for item in form]
            if all([isinstance(item, AstValue) for item in values]):
                return AstValue([item.value for item in values])
            else:
                return AstVector(values)

        else:
            pass


def parse(source):
    if type(source) is str:
        source = tokenize(source)

    if isinstance(source, Form):
        parser = Parser()
        return parser.parse(source)

    raise ValueError("Canot parse input of type '{}'".format(type(source)))
