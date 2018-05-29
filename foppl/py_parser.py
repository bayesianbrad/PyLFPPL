#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 19. Jan 2018, Tobias Kohn
# 31. Jan 2018, Tobias Kohn
#
import ast
from . import Options, foppl_ast
from .distributions import distributions_map

_bin_op = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mult: '*',
    ast.Div: '/',
    ast.FloorDiv: '//',
    ast.Pow: '**',
    ast.Mod: '%',
    ast.Gt: '>',
    ast.GtE: '>=',
    ast.Lt: '<',
    ast.LtE: '<=',
    ast.Eq: '==',
    ast.NotEq: '!=',
    ast.And: 'and',
    ast.Or: 'or',
}

_un_op = {
    ast.USub: '-',
    ast.Not: 'not',
}

class Walker(ast.NodeVisitor):

    def __visit_body(self, body, needs_return=True):
        i = 0
        result = []
        has_return = not needs_return
        while i < len(body):
            item = body[i]
            if isinstance(item, ast.Assign):
                targets = [t.id for t in item.targets]
                source = self.visit(item.value)
                bindings = [(t, source) for t in targets]
                result.append(foppl_ast.AstLet(bindings, self.__visit_body(body[i+1:], needs_return=needs_return)))
                break

            elif isinstance(item, ast.Return):
                has_return = True
                result.append(self.visit(item.value))
                break

            else:
                result.append(self.visit(item))

            i += 1

        if not has_return:
            result.append(foppl_ast.AstValue(None))
        result = [r for r in result if r is not None]
        if len(result) == 0:
            return foppl_ast.AstValue(None)
        elif len(result) == 1:
            return result[0]
        else:
            return foppl_ast.AstBody(result)

    def visit_Assign(self, node: ast.Assign):
        raise NotImplemented

    def visit_BinOp(self, node: ast.BinOp):
        return foppl_ast.AstBinary(_bin_op[node.op.__class__], self.visit(node.left), self.visit(node.right))

    def visit_Call(self, node: ast.Call):
        line_number = getattr(node, 'lineno', -1)
        if isinstance(node.func, ast.Name):
            name = node.func.id
            args = [self.visit(arg) for arg in node.args]
            if name == 'sample':
                if len(args) != 1:
                    raise SyntaxError("wrong number of arguments for 'sample': {}".format(len(args)))
                return foppl_ast.AstSample(args[0], line_number=line_number)
            elif name == 'observe':
                if len(args) != 2:
                    raise SyntaxError("wrong number of arguments for 'observe': {}".format(len(args)))
                return foppl_ast.AstObserve(args[0], args[1], line_number=line_number)
            elif name in distributions_map:
                return foppl_ast.AstDistribution(distributions_map[name], args, line_number=line_number)
            else:
                return foppl_ast.AstFunctionCall(name, args)

        return self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        if len(node.ops) == 1:
            left = self.visit(node.left)
            right = self.visit(node.comparators[0])
            op = _bin_op[node.ops[0].__class__]

            if Options.uniform_conditionals:
                if op == '<=':
                    op = '>='
                    left, right = right, left
                elif op == '>':
                    op = '<'
                    left, right = right, left

                left = foppl_ast.AstBinary('-', left, right)
                right = foppl_ast.AstValue(0)


                if op == '<':
                    compare = foppl_ast.AstCompare('>=', left, right)
                    return foppl_ast.AstUnary('not', compare)
                elif op == '>=':
                    return foppl_ast.AstCompare(op, left, right)

            return foppl_ast.AstCompare(op, left, right)
        else:
            raise SyntaxError("invalid comparison: '{}'".format(ast.dump(node)))

    def visit_Expr(self, node: ast.Expr):
        self.current_line = node.lineno
        return self.visit(node.value)

    def visit_For(self, node: ast.For):
        if isinstance(node.target, ast.Name):
            target = node.target.id
            seq = self.visit(node.iter)
            body = self.__visit_body(node.body, needs_return=False)
            return foppl_ast.AstFor(target, seq, body)
        else:
            raise SyntaxError("'for' requires a variable")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        params = [foppl_ast.AstSymbol(arg.arg) for arg in node.args.args]
        f = foppl_ast.AstFunction(node.name, params, self.__visit_body(node.body))
        return foppl_ast.AstDef(node.name, f)

    def visit_If(self, node: ast.If):
        cond = self.visit(node.test)
        if_body = self.__visit_body(node.body)
        else_body = self.__visit_body(node.orelse) if node.orelse is not None and len(node.orelse) > 0 else None

        if else_body is not None and isinstance(cond, foppl_ast.AstUnary) and cond.op == 'not':
            cond = cond.item
            if_body, else_body = else_body, if_body

        return foppl_ast.AstIf(cond, if_body, else_body)

    def visit_IfExp(self, node: ast.IfExp):
        print(ast.dump(node))
        raise NotImplemented

    def visit_List(self, node: ast.List):
        if all([isinstance(e, ast.Num) for e in node.elts]):
            items = [e.n for e in node.elts]
            return foppl_ast.AstValue(items)
        else:
            items = [self.visit(e) for e in node.elts]
            return foppl_ast.AstVector(items)

    def visit_Module(self, node: ast.Module):
        return self.__visit_body(node.body, needs_return=False)

    def visit_Name(self, node: ast.Name):
        return foppl_ast.AstSymbol(node.id)

    def visit_Num(self, node: ast.Num):
        return foppl_ast.AstValue(node.n)

    def visit_Return(self, node: ast.Return):
        raise NotImplemented

    def visit_Subscript(self, node: ast.Subscript):
        seq = self.visit(node.value)
        if isinstance(node.slice, ast.Index):
            index = self.visit(node.slice.value)
            return foppl_ast.AstFunctionCall('get', [seq, index])
        else:
            raise SyntaxError("subscripting only supported for indices")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        op = _un_op[node.op.__class__]
        item = self.visit(node.operand)
        return foppl_ast.AstUnary(op, item)


def parse(source):
    a = ast.parse(source)
    return Walker().visit(a)
