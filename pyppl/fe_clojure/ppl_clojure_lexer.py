#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Feb 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
from .. import lexer
from ..fe_clojure import ppl_clojure_forms as clj
from ..lexer import CatCode, TokenType


#######################################################################################################################

class ClojureLexer(object):

    def __init__(self, text: str):
        self.text = text
        self.lexer = lexer.Lexer(text)
        self.source = lexer.BufferedIterator(self.lexer)
        self.lexer.catcodes['\n', ','] = CatCode.WHITESPACE
        self.lexer.catcodes['!', '$', '*', '+', '-', '.', '/', '<', '>', '=', '?'] = CatCode.ALPHA
        self.lexer.catcodes[';'] = CatCode.LINE_COMMENT
        self.lexer.catcodes['#', '\'', '`', '~', '^', '@'] = CatCode.SYMBOL
        self.lexer.catcodes['&'] = CatCode.SYMBOL
        self.lexer.catcodes['%', ':'] = CatCode.PREFIX
        self.lexer.add_symbols('~@', '#\'')
        self.lexer.add_string_prefix('#')
        self.lexer.add_constant('false', False)
        self.lexer.add_constant('nil', None)
        self.lexer.add_constant('true', True)

    def __iter__(self):
        return self

    def __next__(self):
        source = self.source
        if source.has_next:
            token = source.next()
            pos, token_type, value = token
            lineno = self.lexer.get_line_from_pos(pos)

            if token_type == TokenType.LEFT_BRACKET:
                left = value
                result = []
                while source.has_next and source.peek()[1] != TokenType.RIGHT_BRACKET:
                    result.append(self.__next__())

                if source.has_next:
                    token = source.next()
                    right = token[2] if token is not None else '<EOF>'
                    if not token[1] == TokenType.RIGHT_BRACKET:
                        raise SyntaxError("expected right parentheses or bracket instead of '{}' (line {})".format(
                            right, self.lexer.get_line_from_pos(token[0])
                        ))
                    if left == '(' and right == ')':
                        return clj.Form(result, lineno=lineno)

                    elif left == '[' and right == ']':
                        return clj.Vector(result, lineno=lineno)

                    elif left == '{' and right == '}':
                        if len(result) % 2 != 0:
                            raise SyntaxError("map requires an even number of elements ({} given)".format(len(result)))
                        return clj.Map(result, lineno=lineno)

                    else:
                        raise SyntaxError("mismatched parentheses: '{}' amd '{}' (line {})".format(
                            left, right, lineno
                        ))

            elif token_type == TokenType.NUMBER:
                return clj.Value(value, lineno=lineno)

            elif token_type == TokenType.STRING:
                return clj.Value(eval(value), lineno=lineno)

            elif token_type == TokenType.VALUE:
                return clj.Value(value, lineno=lineno)

            elif token_type == TokenType.SYMBOL:

                if value == '#':
                    form = self.__next__()
                    if not isinstance(form, clj.Form):
                        raise SyntaxError("'#' requires a form to build a function (line {})".format(lineno))

                    params = clj.Vector(_ParameterExtractor().extract_parameters(form))
                    return clj.Form(['fn', params, form])

                elif value == '@':
                    form = self.__next__()
                    return clj.Form([clj.Symbol('deref', lineno=lineno), form], lineno=lineno)

                elif value == '\'':
                    form = self.__next__()
                    return clj.Form([clj.Symbol('quote', lineno=lineno), form], lineno=lineno)

                elif value == '#\'':
                    form = self.__next__()
                    return clj.Form([clj.Symbol('var', lineno=lineno), form], lineno=lineno)

                return clj.Symbol(value, lineno=lineno)

            else:
                raise SyntaxError("invalid token: '{}' (line {})".format(token_type, lineno))

        raise StopIteration

#######################################################################################################################

class _ParameterExtractor(clj.LeafVisitor):

    def __iter__(self):
        self.parameters = set()

    def visit_symbol(self, node:clj.Symbol):
        n = node.name
        if n.startswith('%'):
            if len(n) == 1:
                self.parameters.add(n)
            elif len(n) == 2 and '1' <= n[1] <= '9':
                self.parameters.add(n)
            else:
                raise SyntaxError("invalid parameter: '{}'".format(n))

    def extract_parameters(self, node):
        self.parameters = set()
        self.visit(node)
        if '%' in self.parameters:
            if len(self.parameters) == 1:
                return ['%']
            raise TypeError("cannot combine parameters '%' and '%1', '%2', ... in one function")
        else:
            count = max([ord(n[1])-ord('0') for n in self.parameters])
            result = ['%' + chr(i + ord('1')) for i in range(count)]
            return result
