#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 02. Mar 2018, Tobias Kohn
# 22. Mar 2018, Tobias Kohn
#
from ..ppl_ast import *
from ..ppl_ast_annotators import get_info


def _is_block(node):
    if isinstance(node, AstBody):
        return len(node) > 1
    elif isinstance(node, AstLet):
        return True
    elif isinstance(node, AstFor) or isinstance(node, AstWhile):
        return True
    elif isinstance(node, AstDef):
        return _is_block(node.value)
    elif isinstance(node, AstIf):
        return node.has_else or _is_block(node.if_node) or _is_block(node.else_node)
    else:
        return False


def _push_return(node, f):
    """
    Rewrites the AST to make a `return` or _assignment_ the last effective statement to be executed.

    For instance, a LISP-based frontend might give us a code fragment such as (in pseudo-code):
       `return (let [x = 12] (x * 3))`
    We cannot translate this directly to Python, as it would result in invalid code, but have to rewrite it to:
       `(let [x = 12] (return x * 3))`

    This pushing of the `return`-statement (or any assignment) into the expression is done by this function. The `node`
    parameter stands for the expression (in the example above the `let`-expression), while `f` is a function that
    takes a node and wraps it into a `return`.

    Sample usage: `_push_return(let_node, lambda x: AstReturn(x))`

    :param node:  The expression into which we need to push the `return` or _assignment_.
    :param f:     A function that takes one argument of type `AstNode` and returns another `AstNode`-object, usually
                  by wrapping its argument into an `AstReturn` or `AstDef`.
    :return:      The original expression with the `return` applied to the last statement to be executed.
    """
    if node is None:
        return None
    elif isinstance(node, AstBody) and len(node) > 1:
        return AstBody(node.items[:-1] + [_push_return(node.items[-1], f)])
    elif isinstance(node, AstLet):
        return AstLet(node.target, node.source, _push_return(node.body, f))
    elif isinstance(node, AstFor):
        return AstFor(node.target, node.source, _push_return(node.body, f))
    elif isinstance(node, AstDef):
        return AstDef(node.name, _push_return(node.value, f))
    elif isinstance(node, AstIf):
        return AstIf(node.test, _push_return(node.if_node, f), _push_return(node.else_node, f))
    elif isinstance(node, AstWhile):
        return AstBody([node, f(AstValue(None))])
    else:
        return f(node)


def _normalize_name(name):
    if type(name) is tuple:
        return ', '.join([_normalize_name(n) for n in name])
    result = ''
    if name.endswith('?'):
        name = 'is_' + name[:-1]
    if name.endswith('!'):
        name = 'do_' + name[:-1]
    for n in name:
        if n in ('+', '-', '?', '!', '_'):
            result += '_'
        elif n == '*':
            result += '_STAR_'
        elif '0' <= n <= '9' or 'A' <= n <= 'Z' or 'a' <= n <= 'z':
            result += n
        elif n == '.':
            result += n
    return result


class CodeGenerator(ScopedVisitor):

    def __init__(self):
        super().__init__()
        self.functions = []
        self.imports = []
        self._symbol_counter_ = 99
        self.short_names = False        # used for debugging
        self.state_object = None        # type:str

    def get_prefix(self):
        import datetime
        result = ['# {}'.format(datetime.datetime.now()),
                  '\n'.join(self.imports),
                  '\n\n'.join(self.functions)]
        return '\n'.join(result)

    def generate_symbol(self):
        self._symbol_counter_ += 1
        return "_{}_".format(self._symbol_counter_)

    def add_function(self, params:list, body:str):
        name = "__LAMBDA_FUNCTION__{}__".format(len(self.functions) + 1)
        self.functions.append("def {}({}):\n\t{}".format(name, ', '.join(params), body.replace('\n', '\n\t')))
        return name

    def visit_attribute(self, node:AstAttribute):
        result = self.visit(node.base)
        return "{}.{}".format(result, node.attr)

    def visit_binary(self, node:AstBinary):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return "({} {} {})".format(left, node.op, right)

    def visit_body(self, node:AstBody):
        if len(node) == 0:
            return "pass"
        items = [self.visit(item) for item in node.items]
        items = [item for item in items if item != '']
        return '\n'.join(items)

    def visit_break(self, _):
        return "break"

    def visit_call(self, node: AstCall):
        function = self.visit(node.function)
        args = [self.visit(arg) for arg in node.args]
        keywords = [''] * node.pos_arg_count + ['{}='.format(key) for key in node.keywords]
        args = [a + b for a, b in zip(keywords, args)]
        return "{}({})".format(function, ', '.join(args))

    def visit_compare(self, node: AstCompare):
        if node.second_right is None:
            left = self.visit(node.left)
            right = self.visit(node.right)
            return "({} {} {})".format(left, node.op, right)
        else:
            left = self.visit(node.left)
            right = self.visit(node.right)
            second_right = self.visit(node.second_right)
            return "({} {} {} {} {})".format(left, node.op, right, node.second_op, second_right)

    def visit_def(self, node: AstDef):
        name = _normalize_name(node.original_name if self.short_names else node.name)
        if self.state_object is not None:
            name = "{}['{}']".format(self.state_object, name)
        if isinstance(node.value, AstFunction):
            function = node.value
            params = function.parameters
            if function.vararg is not None:
                params.append("*" + function.vararg)
            body = self.visit(function.body).replace('\n', '\n\t')
            return "def {}({}):\n\t{}".format(name, ', '.join(params), body)

        elif isinstance(node.value, AstWhile) or isinstance(node.value, AstObserve):
            result = self.visit(node.value)
            return "{}\n{} = None".format(result, name)

        elif _is_block(node.value):
            result = _push_return(node.value, lambda x: AstDef(node.name, x))
            if not isinstance(result, AstDef):
                return self.visit(result)

        return "{} = {}".format(name, self.visit(node.value))

    def visit_dict(self, node: AstDict):
        result = { key: self.visit(node.items[key]) for key in node.items }
        result = ["{}: {}".format(key, result[key]) for key in result]
        return "{" + ', '.join(result) + "}"

    def visit_for(self, node: AstFor):
        name = _normalize_name(node.original_target if self.short_names else node.target)
        source = self.visit(node.source)
        body = self.visit(node.body).replace('\n', '\n\t')
        return "for {} in {}:\n\t{}".format(name, source, body)

    def visit_function(self, node: AstFunction):
        params = node.parameters
        if node.vararg is not None:
            params.append("*" + node.vararg)
        body = self.visit(node.body)
        if '\n' in body or get_info(node.body).has_return:
            return self.add_function(params, body)
        else:
            return "(lambda {}: {})".format(', '.join(params), body)

    def visit_if(self, node: AstIf):
        test = self.visit(node.test)
        if_expr = self.visit(node.if_node)
        if node.has_else:
            else_expr = self.visit(node.else_node)
            if node.has_elif:
                if not else_expr.startswith("if"):
                    enode = node.else_node
                    etest = self.visit(enode.test)
                    ebody = self.visit(enode.if_node)
                    if enode.has_else:
                        else_expr = "if {}:\n\t{}else:\n\t{}:".format(etest, ebody, self.visit(enode.else_body))
                    else:
                        else_expr = "if {}:\n\t{}".format(etest, ebody)
                return "if {}:\n\t{}\nel{}".format(test, if_expr.replace('\n', '\n\t'), else_expr)
            elif '\n' in if_expr or '\n' in else_expr:
                return "if {}:\n\t{}\nelse:\n\t{}".format(test, if_expr.replace('\n', '\n\t'),
                                                          else_expr.replace('\n', '\n\t'))
            else:
                return "{} if {} else {}".format(if_expr, test, else_expr)
        else:
            if '\n' in if_expr:
                return "if {}:\n\t{}".format(test, if_expr.replace('\n', '\n\t'))
            else:
                return "{} if {} else None".format(if_expr, test)

    def visit_import(self, node: AstImport):
        self.imports.append("import {}".format(node.module_name))
        if node.imported_names is None:
            result = "import {}{}".format(node.module_name, "as {}".format(node.alias) if node.alias is not None else '')
        elif len(node.imported_names) == 1 and node.alias is not None:
            result = "from {} import {} as {}".format(node.module_name, node.imported_names[0], node.alias)
        else:
            result = "from {} import {}".format(node.module_name, ', '.join(node.imported_names))
        return ""

    def visit_let(self, node: AstLet):
        name = _normalize_name(node.original_target if self.short_names else node.target)
        if isinstance(node.source, AstLet):
            result = self.visit(AstDef(node.target, node.source))
            return result + "\n{}".format(self.visit(node.body))
        else:
            return "{} = {}\n{}".format(name, self.visit(node.source), self.visit(node.body))

    def visit_list_for(self, node: AstListFor):
        name = _normalize_name(node.original_target if self.short_names else node.target)
        expr = self.visit(node.expr)
        if _is_block(node.expr):
            expr = self.add_function([str(node.target)], expr)
            expr += "({})".format(str(node.target))
        source = self.visit(node.source)
        test = (' if ' + self.visit(node.test)) if node.test is not None else ''
        return "[{} for {} in {}{}]".format(expr, name, source, test)

    def visit_multi_slice(self, node: AstMultiSlice):
        base = self.visit(node.base)
        slices = [self.visit(index) if index is not None else ':' for index in node.indices]
        return "{}[{}]".format(base, ','.join(slices))

    def visit_observe(self, node: AstObserve):
        dist = self.visit(node.dist)
        return "observe({}, {})".format(dist, self.visit(node.value))

    def visit_return(self, node: AstReturn):
        if node.value is None:
            return "return None"
        elif isinstance(node.value, AstWhile) or isinstance(node.value, AstObserve):
            result = self.visit(node.value)
            return result + "\nreturn None"
        elif _is_block(node.value):
            result = _push_return(node.value, lambda x: AstReturn(x))
            if isinstance(result, AstReturn):
                return "return {}".format(self.visit(result))
            else:
                return self.visit(result)
        else:
            return "return {}".format(self.visit(node.value))

    def visit_sample(self, node: AstSample):
        dist = self.visit(node.dist)
        size = self.visit(node.size)
        if size is not None:
            return "sample({}, sample_size={})".format(dist, size)
        else:
            return "sample({})".format(dist)

    def visit_slice(self, node: AstSlice):
        base = self.visit(node.base)
        start = self.visit(node.start) if node.start is not None else ''
        stop = self.visit(node.stop) if node.stop is not None else ''
        return "{}[{}:{}]".format(base, start, stop)

    def visit_subscript(self, node: AstSubscript):
        base = self.visit(node.base)
        index = self.visit(node.index)
        if isinstance(node.base, AstDict) and node.default is not None:
            default = self.visit(node.default)
            return "{}.get({}, {})".format(base, index, default)
        else:
            return "{}[{}]".format(base, index)

    def visit_symbol(self, node: AstSymbol):
        if self.short_names:
            if self.state_object is not None and not node.predef and not '.' in node.original_name:
                return "{}['{}']".format(self.state_object, node.original_name)
            else:
                return node.original_name
        sym = self.resolve(node.name)
        if isinstance(sym, AstSymbol):
            name = _normalize_name(sym.name)
        else:
            name = _normalize_name(node.name)
        if self.state_object is not None and not node.predef and not '.' in name:
            name = "{}['{}']".format(self.state_object, name)
        return name

    def visit_unary(self, node: AstUnary):
        return "{}{}".format(node.op, self.visit(node.item))

    def visit_value(self, node: AstValue):
        return repr(node.value)

    def visit_value_vector(self, node: AstValueVector):
        return repr(node.items)

    def visit_vector(self, node: AstVector):
        return "[{}]".format(', '.join([self.visit(item) for item in node.items]))

    def visit_while(self, node: AstWhile):
        test = self.visit(node.test)
        body = self.visit(node.body).replace('\n', '\n\t')
        return "while {}:\n\t{}".format(test, body)


def generate_code(ast, *, code_generator=None, name=None, parameters=None, state_object=None):
    if code_generator is not None:
        if callable(code_generator):
            cg = code_generator()
        else:
            cg = code_generator
    else:
        cg = CodeGenerator()
    if state_object is not None:
        cg.state_object = state_object

    result = cg.visit(ast)
    if type(result) is list:
        result = [cg.get_prefix()] + result
        result = '\n\n'.join(result)
    else:
        result = cg.get_prefix() + '\n' + result

    if name is not None:
        assert type(name) is str, "name must be a string"
        if parameters is None:
            parameters = ''
        elif type(parameters) in (list, tuple):
            parameters = ', '.join(parameters)
        elif type(parameters) is not str:
            raise TypeError("'parameters' must be a list of strings, or a string")
        result = "def {}({}):\n\t{}".format(name, parameters, result)

    return result
