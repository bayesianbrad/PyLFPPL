#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 27. Feb 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
from ..ppl_ast import *

class ClojureRepr(Visitor):

    def __init__(self):
        super().__init__()
        self.short_names = False  # used for debugging

    def visit_indent(self, node, indent=2):
        if type(indent) is int:
            indent = ' ' * indent
        result = self.visit(node)
        if result is not None:
            result = result.replace('\n', '\n'+indent)
        return result

    def visit_attribute(self, node:AstAttribute):
        base = self.visit(node.base)
        return "(. {} {})".format(base, node.attr)

    def visit_binary(self, node:AstBinary):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return "({} {} {})".format(node.op, left, right)

    def visit_body(self, node:AstBody):
        items = [self.visit_indent(item) for item in node.items]
        return "(do\n  {})".format('\n  '.join(items))

    def visit_break(self, node:AstBreak):
        return "(break)"

    def visit_call(self, node:AstCall):
        function = self.visit(node.function)
        args = [self.visit(item) for item in node.args]
        keywords = [''] * node.pos_arg_count + [':{} '.format(key) for key in node.keywords]
        args = [a + b for a, b in zip(keywords, args)]
        return "({} {})".format(function, ' '.join(args))

    def visit_compare(self, node:AstCompare):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = '=' if node.op == '==' else node.op
        if node.second_right is not None:
            third = self.visit(node.second_right)
            if node.op == node.second_op:
                return "({} {} {} {})".format(op, left, right, third)
            else:
                return "(and ({} {} {}) ({} {} {}))".format(op, left, right, node.second_op, right, third)
        else:
            return "({} {} {})".format(op, left, right)

    def visit_def(self, node:AstDef):
        name = node.original_name if self.short_names else node.name
        value = self.visit_indent(node.value)
        if '\n' in value:
            return "(def {}\n  {})".format(name, value)
        else:
            return "(def {} {})".format(name, value)

    def visit_dict(self, node:AstDict):
        items = ["{} {}".format(key, node.items[key]) for key in node.items]
        return "{" + ', '.join(items) + "}"

    def visit_for(self, node:AstFor):
        name = node.original_target if self.short_names else node.target
        source = self.visit(node.source)
        body = self.visit_indent(node.body)
        return "(doseq [{} {}]\n  {})".format(name, source, body)

    def visit_function(self, node:AstFunction):
        params = node.parameters
        if node.vararg is not None:
            params.append('& ' + node.vararg)
        body = self.visit_indent(node.body)
        return "(fn [{}]\n  {})".format(' '.join(params), body)

    def visit_if(self, node:AstIf):
        test = self.visit(node.test)
        body = self.visit_indent(node.if_node)
        else_body = self.visit_indent(node.else_node)
        if else_body is not None:
            return "(if {}\n  {}\n  {})".format(test, body, else_body)
        else:
            return "(if {}\n  {})".format(test, body)

    def visit_import(self, node:AstImport):
        if node.alias is not None:
            if node.imported_names is None:
                s = ":as {}".format(node.alias)
            else:
                s = "[{} :as {}]".format(node.imported_names[0], node.alias)
            return "(require '{} {})".format(node.module_name, s)
        elif node.imported_names is not None:
            if len(node.imported_names) == 1 and node.imported_names[0] == '*':
                return "(use '{})".format(node.module_name)
            else:
                return "(require '{} :refer [{}])".format(node.module_name, ' '.join(node.imported_names))
        return "(require '{})".format(node.module_name)

    def visit_let(self, node:AstLet):
        name = node.original_target if self.short_names else node.target
        source = self.visit(node.source)
        body = self.visit_indent(node.body)
        return "(let [{} {}]\n  {})".format(name, source, body)

    def visit_list_for(self, node:AstListFor):
        name = node.original_target if self.short_names else node.target
        source = self.visit(node.source)
        body = self.visit_indent(node.expr)
        return "(for [{} {}]\n  {})".format(name, source, body)

    def visit_observe(self, node:AstObserve):
        dist = self.visit(node.dist)
        value = self.visit(node.value)
        return "(observe {} {})".format(dist, value)

    def visit_return(self, node:AstReturn):
        value = self.visit(node.value)
        return "(return {})".format(value)

    def visit_sample(self, node:AstSample):
        dist = self.visit(node.dist)
        return "(sample {})".format(dist)

    def visit_slice(self, node:AstSlice):
        sequence = self.visit(node.base)
        start = self.visit(node.start)
        stop = self.visit(node.stop)
        if stop is None:
            if node.start_as_int == 1:
                return "(rest {})".format(sequence)
            else:
                return "(drop {} {})".format(sequence, start)
        elif start is None:
            return "(take {} {})".format(sequence, stop)
        else:
            return "(subvec {} {} {})".format(sequence, start, stop)

    def visit_subscript(self, node:AstSubscript):
        sequence = self.visit(node.base)
        index = self.visit(node.index)
        return "(get {} {})".format(sequence, index)

    def visit_symbol(self, node:AstSymbol):
        return node.original_name if self.short_names else node.name

    def visit_unary(self, node:AstUnary):
        item = self.visit(node.item)
        return "({} {})".format(node.op, item)

    def visit_value(self, node:AstValue):
        return repr(node)

    def visit_value_vector(self, node:AstValueVector):
        items = [repr(item) for item in node.items]
        return "[{}]".format(' '.join(items))

    def visit_vector(self, node:AstVector):
        items = [self.visit(item) for item in node.items]
        return "[{}]".format(' '.join(items))

    def visit_while(self, node:AstWhile):
        test = self.visit(node.test)
        body = self.visit_indent(node.body)
        return "(while {}\n  {})".format(test, body)


def dump(ast):
    """
    Returns a string-representation of the AST which is valid `Clojure`-code.

    :param ast:  The AST representing the program.
    :return:     A string with valid `Clojure`-code.
    """
    result = ClojureRepr().visit(ast)
    if type(result) is list:
        return '\n'.join(result)
    else:
        return result
