#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 19. Feb 2018, Tobias Kohn
# 22. Mar 2018, Tobias Kohn
#
from ..ppl_ast import *
from ..ppl_namespaces import namespace_from_module
import ast


_cl = ast.copy_location


class _FunctionContext(object):

    def __init__(self, prev):
        self.prev = prev
        self.global_names = set()

    def add_global(self, name:str):
        self.global_names.add(name)

    def is_global(self, name:str):
        return name in self.global_names


class PythonParser(ast.NodeVisitor):

    __ast_ops__ = {
        ast.Add:    '+',
        ast.Sub:    '-',
        ast.Mult:   '*',
        ast.Div:    '/',
        ast.FloorDiv: '//',
        ast.Mod:    '%',
        ast.Pow:    '**',
        ast.LShift: '<<',
        ast.RShift: '>>',
        ast.UAdd:   '+',
        ast.USub:   '-',
        ast.Eq:     '==',
        ast.NotEq:  '!=',
        ast.Lt:     '<',
        ast.Gt:     '>',
        ast.LtE:    '<=',
        ast.GtE:    '>=',
        ast.And:    'and',
        ast.Or:     'or',
        ast.Not:    'not',
        ast.BitAnd: '&',
        ast.BitOr:  '|',
        ast.Is:     'is',
        ast.IsNot:  'is not',
        ast.In:     'in',
        ast.NotIn:  'not in',
    }

    def __init__(self):
        self.function_context = None  # type:_FunctionContext

    def _enter_function(self):
        self.function_context = _FunctionContext(self.function_context)

    def _leave_function(self):
        self.function_context = self.function_context.prev

    def _add_global_name(self, name:str):
        result = self.function_context is not None
        if result:
            self.function_context.add_global(name)
        return result

    def _is_global_name(self, name:str):
        if self.function_context is None:
            return True
        else:
            return self.function_context.is_global(name)

    def _visit_body(self, body:list, require_return:bool=False):
        if len(body) == 1 and isinstance(body[0], ast.Pass):
            if require_return:
                return _cl(AstReturn(AstValue(None)), body[0])
            else:
                return _cl(makeBody([]), body[0])

        result = []
        for item in body:
            v_item = self.visit(item)
            if isinstance(v_item, AstBody):
                result += v_item.items
            elif v_item is not None:
                result.append(v_item)

        if require_return:
            if len(result) == 0:
                return AstReturn(AstValue(None))
            elif not isinstance(result[-1], AstReturn):
                result.append(AstReturn(AstValue(None)))

        for i in range(len(result)):
            if isinstance(result[i], AstReturn) or isinstance(result[i], AstBreak):
                result = result[:i+1]
                break

        if len(result) == 1:
            return result[0]
        else:
            return makeBody(result)

    def generic_visit(self, node):
        raise NotImplementedError("cannot compile '{}'".format(ast.dump(node)))

    def visit_Assign(self, node:ast.Assign):
        source = self.visit(node.value)
        if len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                return _cl(makeDef(target.id, source, self._is_global_name(target.id)), node)

            elif isinstance(target, ast.Tuple) and all([isinstance(t, ast.Name) for t in target.elts]):
                return _cl(makeDef(tuple(t.id for t in target.elts), source), node)

            elif isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and \
                    isinstance(target.slice, ast.Index):
                base = target.value.id
                index = target.slice.value
                return _cl(AstCall(AstSymbol('list.put'), [self.visit(base), self.visit(index), source],
                                   is_builtin=True), node)

        elif len(node.targets) > 1 and all(isinstance(target, ast.Name) for target in node.targets):
            result = []
            base = node.targets[-1].id
            result.append(_cl(makeDef(base, source, self._is_global_name(base)), node))
            base_name = AstSymbol(base)
            for target in node.targets[:-1]:
                result.append(makeDef(target.id, base_name, self._is_global_name(target.id)))
            return makeBody(result)

        raise NotImplementedError("cannot compile assignment '{}'".format(ast.dump(node)))

    def visit_Attribute(self, node:ast.Attribute):
        base = self.visit(node.value)
        return _cl(AstAttribute(base, node.attr), node)

    def visit_AugAssign(self, node:ast.AugAssign):
        if isinstance(node.target, ast.Name):
            target = node.target.id
            source = self.visit(node.value)
            op = self.__ast_ops__[node.op.__class__]
            return _cl(makeDef(target, AstBinary(AstSymbol(target), op, source)), node)
        raise NotImplementedError("cannot assign to '{}'".format(ast.dump(node.target)))

    def visit_BinOp(self, node:ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.__ast_ops__[node.op.__class__]
        return _cl(AstBinary(left, op, right), node)

    def visit_Break(self, node:ast.Break):
        return _cl(AstBreak(), node)

    def visit_Call(self, node:ast.Call):
        def _check_arg_arity(name, args, arg_count):
            if len(args) != arg_count:
                if arg_count == 0:
                    s = "no arguments"
                elif arg_count == 1:
                    s = "one argument"
                elif arg_count == 2:
                    s = "two arguments"
                elif arg_count == 3:
                    s = "three arguments"
                else:
                    s = "{} arguments".format(arg_count)
                raise TypeError("{}() takes exactly {} ({} given)".format(name, s, len(args)))

        if isinstance(node.func, ast.Attribute):
            attr_base = self.visit(node.func.value)
            attr_name = node.func.attr
            args = [self.visit(arg) for arg in node.args]
            keywords = []
            for kw in node.keywords:
                keywords.append(kw.arg)
                args.append(self.visit(kw.value))
            if attr_name in ['append', 'extend', 'insert', 'remove', 'index']:
                if len(keywords) > 0:
                    raise SyntaxError("extra keyword arguments for '{}'".format(attr_name))
                return _cl(AstCall(AstSymbol('list.' + attr_name, predef=True), [attr_base] + args,
                                   is_builtin=True), node)
            elif attr_name in ['get', 'keys', 'items', 'values', 'update']:
                if len(keywords) > 0:
                    raise SyntaxError("extra keyword arguments for '{}'".format(attr_name))
                return _cl(AstCall(AstSymbol('dict.' + attr_name, predef=True), [attr_base] + args,
                                   is_builtin=True), node)
            return _cl(AstCall(AstAttribute(attr_base, attr_name), args, keywords), node)

        elif isinstance(node.func, ast.Name):
            name = node.func.id
            args = [self.visit(arg) for arg in node.args]
            keywords = []
            for kw in node.keywords:
                keywords.append(kw.arg)
                args.append(self.visit(kw.value))
            if name == 'sample':
                if len(args) == 2 and (len(keywords) == 0 or
                                                (len(keywords) == 1 and keywords[0] in ('sample_size', 'size'))):
                    size = args[1]
                elif len(keywords) > 0:
                    raise SyntaxError("extra keyword arguments for '{}'".format(name))
                else:
                    _check_arg_arity(name, args, 1)
                    size = None
                result = AstSample(args[0], size=size)
            elif name == 'observe':
                _check_arg_arity(name, args, 2)
                if len(keywords) > 0:
                    raise SyntaxError("extra keyword arguments for '{}'".format(name))
                result = AstObserve(args[0], args[1])
            elif name in ('abs', 'divmod', 'filter', 'format', 'len', 'map', 'max', 'min', 'pow', 'print', 'range',
                          'reversed', 'round', 'sorted', 'sum', 'zip'):
                result = AstCall(AstSymbol(name, predef=True), args, keywords, is_builtin=True)
            else:
                result = AstCall(AstSymbol(name), args, keywords)
            return _cl(result, node)

        elif isinstance(node.func, ast.Lambda):
            func = self.visit_Lambda(node.func)
            args = [self.visit(arg) for arg in node.args]
            keywords = []
            for kw in node.keywords:
                keywords.append(kw.arg)
                args.append(self.visit(kw.value))
            return _cl(AstCall(func, args, keywords), node)

        else:
            raise NotImplementedError("a function call needs a function name, not '{}'".format(ast.dump(node.func)))

    def visit_Compare(self, node:ast.Compare):
        if len(node.ops) == 1:
            op = self.__ast_ops__[node.ops[0].__class__]
            left = self.visit(node.left)
            right = self.visit(node.comparators[0])
            if op in ('is', 'is not') and (is_boolean(right) or is_none(right)):
                op = '==' if op == 'is' else '!='
            return _cl(AstCompare(left, op, right), node)

        elif len(node.ops) == 2:
            op1 = self.__ast_ops__[node.ops[0].__class__]
            op2 = self.__ast_ops__[node.ops[1].__class__]
            if (op1 in ['<', '<='] and op2 in ['<', '<=']) or \
               (op1 in ['>', '>='] and op2 in ['>', '>=']):
                left = self.visit(node.left)
                middle = self.visit(node.comparators[0])
                right = self.visit(node.comparators[1])
                return _cl(AstCompare(left, op1, middle, op2, right), node)

        raise NotImplementedError("cannot compile compare '{}'".format(ast.dump(node)))

    def visit_Dict(self, node:ast.Dict):
        keys = [self.visit(key) for key in node.keys]
        values = [self.visit(value) for value in node.values]
        result = {}
        for key, value in zip(keys, values):
            if isinstance(key, AstValue):
                result[key.value] = value
            else:
                raise SyntaxError("key to dict must be primitive type, not '{}'".format(key))
        return AstDict(result)

    def visit_Expr(self, node:ast.Expr):
        return self.visit(node.value)

    def visit_For(self, node:ast.For):
        if len(node.orelse) > 0:
            raise NotImplementedError("'else' is not supported for for-loops")

        iter_ = self.visit(node.iter)
        body = self._visit_body(node.body)
        if isinstance(node.target, ast.Name):
            return _cl(makeFor(node.target.id, iter_, body), node)

        elif isinstance(node.target, ast.Tuple) and all([isinstance(t, ast.Name) for t in node.target.elts]):
            return _cl(makeFor(tuple(t.id for t in node.target.elts), iter_, body), node)

        raise NotImplementedError("cannot compile for-loop: '{}'".format(ast.dump(node)))

    def visit_FunctionDef(self, node:ast.FunctionDef):
        # TODO: Support default and keyword arguments
        # node.name: str
        # node.args: arguments(arg, varargs, kwonlyargs, kw_defaults, kwarg, defaults
        if len(node.decorator_list) > 0:
            raise NotImplementedError("cannot compile decorators: '{}'".format(ast.dump(node)))
        name = node.name
        arg_names = [arg.arg for arg in node.args.args]
        self._enter_function()
        try:
            body = self._visit_body(node.body, require_return=True)
        finally:
            self._leave_function()
        return makeDef(name, _cl(AstFunction(name, arg_names, body), node), self.function_context is None)

    def visit_Global(self, node:ast.Global):
        for name in node.names:
            if not self._add_global_name(name):
                raise SyntaxError("global outside function")

    def visit_If(self, node:ast.If):
        test = self.visit(node.test)
        body = self._visit_body(node.body)
        else_body = self._visit_body(node.orelse) if len(node.orelse) > 0 else None
        return _cl(makeIf(test, body, else_body), node)

    def visit_IfExp(self, node:ast.IfExp):
        test = self.visit(node.test)
        body = self.visit(node.body)
        else_body = self.visit(node.orelse)
        return _cl(makeIf(test, body, else_body), node)

    def visit_Import(self, node:ast.Import):
        result = []
        for alias in node.names:
            result.append( _cl(AstImport(alias.name, None, alias.asname), node) )
        if len(result) == 1:
            return _cl(result[0], node)
        else:
            return _cl(makeBody(result), node)

    def visit_ImportFrom(self, node:ast.ImportFrom):
        if node.level != 0:
            raise NotImplementedError("cannot import with level != 0: '{}'".format(ast.dump(node)))
        module = node.module
        if len(node.names) == 1 and node.names[0].name == '*':
            _, names = namespace_from_module(module)
            if len(names) > 0:
                return _cl(AstImport(module, names), node)
            else:
                raise NotImplementedError("cannot import '{}'".format(ast.dump(node)))

        elif all([n.asname is None for n in node.names]):
            return _cl(AstImport(module, [n.name for n in node.names]), node)

        else:
            result = []
            for alias in node.names:
                result.append(_cl(AstImport(module, [alias.name], alias.asname), node))
            return _cl(makeBody(result), node)

    def visit_Lambda(self, node: ast.Lambda):
        arg_names = [arg.arg for arg in node.args.args]
        body = AstReturn(self.visit(node.body))
        return _cl(AstFunction(None, arg_names, body), node)

    def visit_List(self, node:ast.List):
        items = [self.visit(item) for item in node.elts]
        return _cl(makeVector(items), node)

    def visit_ListComp(self, node:ast.ListComp):
        if len(node.generators) != 1:
            raise NotImplementedError("a list comprehension must have exactly one generator: '{}'".format(ast.dump(node)))
        if len(node.generators[0].ifs) > 1:
            raise NotImplementedError("a list comprehension must have at most one if: '{}'".format(ast.dump(node)))

        generator = node.generators[0]
        expr = self.visit(node.elt)
        test = self.visit(generator.ifs[0]) if len(generator.ifs) > 0 else None
        target = generator.target
        source = self.visit(generator.iter)
        if isinstance(target, ast.Name):
            return _cl(makeListFor(target.id, source, expr, test), node)

        elif isinstance(target, ast.Tuple) and all([isinstance(t, ast.Name) for t in node.target.elts]):
            return _cl(makeListFor(tuple(t.id for t in node.target.elts), source, expr, test), node)

        raise NotImplementedError("cannot compile list comprehension: '{}'".format(ast.dump(node)))

    def visit_Module(self, node:ast.Module):
        body = self._visit_body(node.body)
        return _cl(body, node)

    def visit_Name(self, node:ast.Name):
        return _cl(AstSymbol(node.id), node)

    def visit_NameConstant(self, node: ast.NameConstant):
        return _cl(AstValue(node.value), node)

    def visit_Num(self, node:ast.Num):
        return _cl(AstValue(node.n), node)

    def visit_Return(self, node:ast.Return):
        if self.function_context is None:
            raise SyntaxError("return outside function")
        return _cl(AstReturn(self.visit(node.value)), node)

    def visit_Str(self, node:ast.Str):
        return _cl(AstValue(node.s), node)

    def visit_Subscript(self, node:ast.Subscript):
        base = self.visit(node.value)
        if isinstance(node.slice, ast.Index):
            index = self.visit(node.slice.value)
            return _cl(AstSubscript(base, index), node)
        elif isinstance(node.slice, ast.Slice) and node.slice.step is None:
            start = self.visit(node.slice.lower)
            stop = self.visit(node.slice.upper)
            return _cl(AstSlice(base, start, stop), node)
        elif isinstance(node.slice, ast.ExtSlice):
            indices = []
            for slice in node.slice.dims:
                if isinstance(slice, ast.Slice) and slice.lower is slice.upper is slice.step is None:
                    indices.append(None)
                elif isinstance(slice, ast.Index):
                    indices.append(self.visit(slice.value))
                else:
                    indices = None
                    break
            if indices is not None:
                return _cl(AstMultiSlice(base, indices), node)
        raise NotImplementedError("cannot compile subscript '{}'".format(ast.dump(node)))

    def visit_Tuple(self, node:ast.Tuple):
        items = [self.visit(item) for item in node.elts]
        return _cl(makeVector(items), node)

    def visit_UnaryOp(self, node:ast.UnaryOp):
        op = self.__ast_ops__[node.op.__class__]
        if isinstance(node.operand, ast.Num) and op in ['+', '-']:
            n = -node.operand.n if op == '-' else node.operand.n
            return _cl(AstValue(n), node)
        else:
            return _cl(AstUnary(op, self.visit(node.operand)), node)

    def visit_While(self, node:ast.While):
        if len(node.orelse) > 0:
            raise NotImplementedError("'else' is not supported for while-loops")

        test = self.visit(node.test)
        body = self._visit_body(node.body)
        return AstWhile(test, body)


#######################################################################################################################

def parse(source):
    py_ast = ast.parse(source)
    ppl_ast = PythonParser().visit(py_ast)
    return ppl_ast
