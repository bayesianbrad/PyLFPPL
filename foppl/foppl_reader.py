#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 29. Nov 2017, Tobias Kohn
# 21. Jan 2018, Tobias Kohn
#
from .foppl_objects import *

def is_alpha(c):
    return 'A' <= c <= 'Z' or 'a' <= c <= 'z' or c in ['_']

def is_alpha_numeric(c):
    return is_alpha(c) or '0' <= c <= '9'

def is_digit(c):
    return '0' <= c <= '9'

def is_hex_digit(c):
    return '0' <= c <= '9' or 'A' <= c <= 'F' or 'a' <= c <= 'f'

def is_identifier(c):
    return is_alpha(c) or '0' <= c <= '9' or c in ['*', '+', '!', '-', '_', '\'', '?', '=']

def is_identifier_start(c):
    return is_identifier(c) and not is_digit(c)

def is_whitespace(c):
    return c <= ' ' or c in [',']

def create_is_numeric_for_radix(radix):
    def is_numeric(c):
        if '0' <= c <= '9':
            return ord(c) - ord('0') < radix
        elif 'A' <= c <= 'F':
            return ord(c) - ord('A') + 10 < radix
        elif 'a' <= c <= 'f':
            return ord(c) - ord('a') + 10 < radix
        else:
            return False
    return is_numeric

_character_names = {
    'space': ' ',
    'newline': '\n',
    'tab': '\t',
    'formfeed': '\f',
    'backspace': '\b',
    'return': '\r'
}


class CharacterStream(object):

    def __init__(self, source):
        self._source = source
        self._offset = 0

    def peek(self, index = 0):
        offset = self._offset + index
        if 0 <= offset < len(self._source):
            return self._source[offset]
        else:
            return None

    def next(self):
        offset = self._offset
        src = self._source
        if offset < len(src):
            self._offset += 1
            self.skip_space()
            return src[offset]
        else:
            return None

    def current_line(self):
        result = 1
        for i in range(self._offset):
            if self._source[i] == '\n':
                result += 1
        return result

    def read(self, count):
        offset = self._offset
        new_offset = min(offset + count, len(self._source))
        self._offset = new_offset
        return self._source[offset:new_offset]

    def read_character(self):
        self.skip()
        name = self.read_while(is_alpha)
        if len(name) == 1:
            return name

        elif name in _character_names.keys():
            return _character_names[name]

        elif name == 'u' and is_hex_digit(self.peek()):
            return str(int(self.read(4), 16))

        elif name == 'o' and is_digit(self.peek()):
            return str(int(self.read(3), 8))

        else:
            return '?'

    def read_integer(self):
        if self.peek() in ['+', '-']:
            sign = -1 if self.peek() == '-' else 1
            self.skip()
        else:
            sign = 1
        result = int(self.read_while(is_digit))
        return sign * result

    def read_number(self):
        c = self.peek()
        sign = -1 if c == '-' else 1
        if c in ['+', '-']:
            c = self.skip()

        if c == '0' and self.peek(1) in ['B', 'b']:
            self.skip(2)
            result = int(self.read_while(['0', '1']), 2)
            return sign * result

        elif c == '0' and self.peek(1) in ['X', 'x']:
            self.skip(2)
            result = int(self.read_while(is_hex_digit), 16)
            return sign * result

        else:
            value = str(self.read_integer())
            c = self.peek()
            if c in ['n', 'N', 'm', 'M']:
                self.skip()
                return int(value)

            if c in ['r', 'R']:
                radix = int(value)
                value = int(self.read_while(create_is_numeric_for_radix(radix)), radix)
                return sign * value

            if c == '.' and is_digit(self.peek(1)):
                self.skip()
                value += '.' + self.read_while(is_digit)
            elif c == '.' and not is_alpha_numeric(self.peek(1)):
                self.skip()
                value += '.0'
            elif c not in ['e', 'E']:
                return sign * int(value)

            if c in ['e', 'E'] and (is_digit(self.peek(1)) or (self.peek(1) in ['+', '-'] and is_digit(self.peek(2)))):
                self.skip()
                value += 'e' + str(self.read_integer())

            return sign * float(value)

    def read_string_literal(self):
        i = self._offset + 1
        src = self._source
        while i < len(src) and src[i] != '"':
            if src[i] == '\\':
                i += 2
            else:
                i += 1
        if i < len(src) and src[i] == '"':
            i += 1
            result = eval(src[self._offset:i])
            self._offset = i
            return result
        else:
            result = eval(src[self._offset:i])
            self._offset = i
            return result

    def _do_read_symbol(self):
        result = self.read_while(is_identifier)
        while self.peek(0) in ['.', ':'] and is_identifier(self.peek(1)):
            result += self.next() + self.read_while(is_identifier)
        return result

    def read_symbol(self):
        c = self.peek()
        if c == '/' and not is_identifier_start(self.peek(1)):
            return self.next()

        elif c == ':':
            result = self.next()
            if self.peek() == ':':
                result += self.next()
            result += self.read_while(is_identifier)
            if self.peek() == '/':
                result += self.next() + self.read_while(is_identifier)

        elif c == '.' and not is_identifier(self.peek(1)):
            return self.next()

        elif c in ['<', '>']:
            self.next()
            if self.peek() == '=':
                return c + self.next()
            else:
                return c

        elif c in ['=']:
            return self.next()

        else:
            result = self._do_read_symbol()
            if self.peek() == '/':
                result += self.next() + self._do_read_symbol()
            if self.peek() == '.':
                result += self.next()

            if result == 'true':
                result = Value(True)
            elif result == 'false':
                result = Value(False)
            elif result == 'nil':
                result = Value(None)

            return result

    def read_while(self, p):
        if type(p) in [list, tuple]:
            return self.read_while(lambda c: c in p)
        i = self._offset
        src = self._source
        while i < len(src) and p(src[i]):
            i += 1
        result = src[self._offset:i]
        self._offset = i
        return result

    def skip(self, count = 1):
        self._offset = min(self._offset + count, len(self._source))
        return self.peek()

    def skip_line_comment(self):
        i = self._offset
        src = self._source
        while i < len(src) and src[i] != '\n':
            i += 1
        if i < len(src) and src[i] == '\n':
            i += 1
        self._offset = i
        c = self.skip_while(is_whitespace)
        if c == ';':
            return self.skip_line_comment()
        else:
            return c

    def skip_space(self):
        c = self.skip_while(is_whitespace)
        if c == ';':
            return self.skip_line_comment()
        else:
            return c

    def skip_while(self, p):
        self.read_while(p)
        return self.peek()


class Reader(object):

    def __init__(self, source):
        if isinstance(source, CharacterStream):
            self._source = source
        else:
            self._source = CharacterStream(source)

    def __iter__(self):
        return self

    def __next__(self):
        src = self._source
        src.skip_space()
        c = src.peek()

        if c is None:
            raise StopIteration()

        elif c == '"':
            return src.read_string_literal()

        elif c == '\\':
            return src.read_character()

        elif is_digit(c) or (c in ['+', '-'] and is_digit(src.peek(1))):
            return src.read_number()

        elif c in ['(', '[', '{']:
            line_number = src.current_line()
            first_char = src.next()
            result = []
            while src.skip_space() not in [None, ')', ']', '}']:
                result.append(self.__next__())

            if src.peek() in [')', ']', '}']:
                src.next()

            if first_char == '(':
                result = Form(result)
            elif first_char == '[':
                result = Vector(result)
            elif first_char == '{':
                raise NotImplementedError()

            result.line_number = line_number
            return result

        elif c == '\'':
            return Form([Symbol.QUOTE, self.__next__()])

        elif c == '@':
            return Form([Symbol.DEREF, self.__next__()])

        elif c == '#':
            c = src.peek(1)
            if c == '{':
                src.skip(2)
                result = []
                while src.peek() not in [None, '}']:
                    result.append(self.__next__())

                if src.peek() == '}':
                    src.next()
                    raise NotImplementedError()
                    # return Set(result)

            elif c == '\'':
                src.skip(2)
                return Form([Symbol.VAR, self.__next__()])

            elif c == '_':
                src.skip(2)
                self.__next__()
                return self.__next__()

            elif c == '(':
                src.skip(2)
                self.__reading_fn = True
                try:
                    self.__arg_count = 0
                    result = []
                    while src.peek() not in [None, ')']:
                        result.append(self.__next__())
                finally:
                    self.__reading_fn = False

                if src.peek() == ')':
                    src.next()
                    if self.__arg_count == -1:
                        args = Vector(['%'])
                    else:
                        args = Vector([Symbol('%' + str(i+1)) for i in range(self.__arg_count)])
                        self.__arg_count = 0
                    return Form([Symbol.FN, args, Form(result)])

            elif c == '"':
                pass

            raise NotImplementedError()

        elif c in ['`', '~']:
            raise NotImplementedError()

        elif c == '%':
            src.next()
            if is_digit(src.peek()):
                c = src.next()
                arg = ord(c) - ord('0')
                if self.__arg_count >= 0:
                    self.__arg_count = max(self.__arg_count, arg)
                return Symbol("%" + c)

            else:
                if self.__arg_count <= 0:
                    self.__arg_count = -1
                return Symbol("%")

        elif c is not None:
            result = src.read_symbol()
            if type(result) is str:
                if result[0] == ':':
                    raise NotImplementedError()
                    #return Keyword(result)

                else:
                    return Symbol(result)

            elif type(result) is tuple:
                return result[0]

            elif type(result) is Value:
                return result

        raise StopIteration()

    def current_line_number(self):
        self._source.current_line()


def tokenize(input):
    reader = Reader(input)
    return Form([Symbol.DO] + list(reader))
