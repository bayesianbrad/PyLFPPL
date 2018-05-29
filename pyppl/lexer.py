#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Feb 2018, Tobias Kohn
# 22. Feb 2018, Tobias Kohn
#
import enum

#######################################################################################################################

class TokenType(enum.Enum):
    SYMBOL = 1
    NUMBER = 2
    STRING = 3
    KEYWORD = 4
    INDENT = 5
    DEDENT = 6
    LEFT_BRACKET = 7
    RIGHT_BRACKET = 8
    NEWLINE = 9
    VALUE = 10


#######################################################################################################################

class CatCode(enum.Enum):
    INVALID = 0
    IGNORE = 1
    WHITESPACE = 2
    ALPHA = 3
    NUMERIC = 4
    SYMBOL = 5
    DELIMITER = 6
    LEFT_BRACKET = 7
    RIGHT_BRACKET = 8
    NEWLINE = 9
    STRING_DELIMITER = 10
    ESCAPE = 11
    PREFIX = 12
    LINE_COMMENT = 13


class CategoryCodes(object):
    """
    This is basically a list that assigns a category code to each character in the ASCII range.
    """

    def __init__(self, char_range:int=128):
        self.catcodes = [CatCode.INVALID for _ in range(char_range)]
        self.catcodes[ord('\t')] = CatCode.WHITESPACE
        self.catcodes[ord('\n')] = CatCode.NEWLINE
        self.catcodes[ord('\r')] = CatCode.WHITESPACE
        self.catcodes[ord(' ')] = CatCode.WHITESPACE
        self.catcodes[ord('_')] = CatCode.ALPHA
        for i in range(ord('!'), ord('A')):
            self.catcodes[i] = CatCode.SYMBOL
        for i in range(ord('0'), ord('9')+1):
            self.catcodes[i] = CatCode.NUMERIC
        for i in range(ord('A'), ord('Z')+1):
            self.catcodes[i] = CatCode.ALPHA
        for i in range(ord('a'), ord('z')+1):
            self.catcodes[i] = CatCode.ALPHA
        for i in ['(', '[', '{']:
            self.catcodes[ord(i)] = CatCode.LEFT_BRACKET
        for i in [')', ']', '}']:
            self.catcodes[ord(i)] = CatCode.RIGHT_BRACKET
        for i in ['\'', '\"']:
            self.catcodes[ord(i)] = CatCode.STRING_DELIMITER

    def __getitem__(self, item):
        if type(item) is str and len(item) == 1:
            return self.catcodes[ord(item)]
        elif type(item) is int and 0 <= item < len(self.catcodes):
            return self.catcodes[ord(item)]
        else:
            raise TypeError("'{}' is not a valid character".format(item))

    def __setitem__(self, key, value):
        if type(key) is str and len(key) == 1:
            key = ord(key)
            self.catcodes[key] = value
        elif type(key) is int and 0 <= key < len(self.catcodes):
            self.catcodes[key] = value
        elif type(key) is tuple:
            for k in key:
                self.__setitem__(k, value)
        elif type(key) is slice:
            start = key.start
            stop = key.stop
            if start is not None and stop is not None and key.step is None:
                if type(start) is str:
                    start = ord(start)
                if type(stop) is str:
                    stop = ord(stop)
                for i in range(start, stop):
                    self.catcodes[i] = value
        else:
            raise TypeError("'{}' is not a valid character".format(key))


#######################################################################################################################

class CharacterStream(object):

    def __init__(self, source:str):
        self.source = source # type:str
        self._pos = 0        # type:int
        self.default_char = '\u0000'  # type:str

    def __getitem__(self, item):
        if 0 <= item < len(self.source):
            return self.source[item]
        else:
            return self.default_char

    def __len__(self):
        return len(self.source)

    def __get_predicate(self, p):
        if len(p) == 1 and callable(p[0]):
            return p[0]
        elif len(p) == 1 and type(p[0]) in [list, tuple]:
            return lambda c: c in p[0]
        else:
            return lambda c: c in p

    def drop(self, count:int):
        if count > 0:
            p = self._pos + count
            self._pos = min(p, len(self.source))

    def drop_if(self, *p):
        p = self.__get_predicate(p)
        i = self._pos
        s = self.source
        result = i < len(s) and p(s[i])
        if result:
            self._pos += 1
        return result

    def drop_while(self, *p):
        p = self.__get_predicate(p)
        i = self._pos
        s = self.source
        while i < len(s) and p(s[i]):
            i += 1
        self._pos = i

    def eof(self):
        return self._pos >= len(self.source)

    def get_line_from_pos(self, pos):
        return self.source.count('\n', 0, pos)

    def next(self):
        i = self._pos
        s = self.source
        if i < len(s):
            self._pos += 1
            return s[i]
        else:
            return self.default_char

    def peek(self, index=0):
        return self.__getitem__(self._pos + index)

    def peek_string(self, count:int):
        if self._pos < len(self.source):
            return self.source[self._pos:self._pos+count]
        else:
            return ''

    def skip(self, count:int):
        self._pos = min(len(self.source), self._pos + count)

    def take(self, count:int):
        if count > 0:
            p = self._pos
            result = self.source[p:p+count]
            self._pos = min(len(self.source), p+count)
            return result
        else:
            return ''

    def take_if(self, *p):
        p = self.__get_predicate(p)
        i = self._pos
        s = self.source
        if i < len(s) and p(s[i]):
            self._pos += 1
            return s[i]
        else:
            return ''

    def take_while(self, *p):
        p = self.__get_predicate(p)
        i = self._pos
        s = self.source
        while i < len(s) and p(s[i]):
            i += 1
        result = s[self._pos:i]
        self._pos = i
        return result

    def test(self, s):
        if s is None:
            return False
        p = self._pos
        source = self.source
        if p >= len(source):
            return False
        if len(s) == 1:
            return source[p] == s
        else:
            return source[p:p+len(s)] == s

    @property
    def current(self):
        return self.__getitem__(self._pos)

    @property
    def current_line(self):
        return self.get_line_from_pos(self._pos)

    @property
    def current_pos(self):
        return self._pos

    @property
    def remaining(self):
        return len(self.source) - self._pos

    @classmethod
    def from_file(cls, filename:str):
        with open(filename, 'r') as f:
            source = ''.join(list(f.readlines()))
        return CharacterStream(source)

    @classmethod
    def from_string(cls, text:str):
        return CharacterStream(text)


#######################################################################################################################

class Lexer(object):
    """
    The lexer takes a string or `CharacterStream` as input, and then reads token by token from this source. It is
    intended to be used as an iterator, and can be adapted by overriding/changing some of its methods or fields.

    - Adapt the category codes of any characters, or even supplant the field `catcodes` by a new `CategoryCodes`-
      object.
    - Use the method `add_keyword(kw)` if you want to register a special name as a keyword. The field `keywords`
      is a set of all keywords as strings.
    - The field `ext_symbols` is used for symbols that span more than one character (such as, e.g., `+=` or `<<`).
      If you want the lexer to recognise special multi-character-symbols, add them to this set of strings. However,
      note that adding the string might not be enough: in fact, the lexer recognises symbols only if each individual
      character of it has category code `SYMBOL`.
    - You can set the fields `line_comment`, or `block_comment_start` and `block_comment_end`, or both in order to
      have the lexer recognise various comments inside the code. Each of this field is either `None` or a string.
      Commenting strings do not depend on any special category codes but are always recognised. This could lead to
      problems if you choose an alphanumeric commenting delimiter, such as `rem`, say, as the lexer would see this
      commenting delimiter also in instances like `remote` or `lorem ipsum`.

    NB: numbers starting with a digit 0, 1, ..., 9 or a sign `+`/`-` and a digit are always recognised as numbers,
    independent of any category codes.
    """

    def __init__(self, source):
        if type(source) is str:
            source = CharacterStream.from_string(source)
        self.source = source                    # type:CharacterStream
        self.catcodes = CategoryCodes()
        self.keywords = set()                   # type:set
        self.ext_symbols = {
            '+=', '-=', '*=', '/=', '%=',
            '<=', '>=', '==', '!=',
            '<<', '>>', '**', '//',
            '&&', '||', '&=', '|='
            '===', '<<=', '>>=', '**=', '//=',
            '..', '...',
            '<~', '~>',
        }
        self.escapes = {
            '\\\n': None,
        }
        self.constants = {}
        self.string_prefix = set()
        self.line_comment = None
        self.block_comment_start = None
        self.block_comment_end = None
        assert isinstance(source, CharacterStream)

    def __iter__(self):
        return self

    def __next__(self):
        source = self.source
        pos = source.current_pos
        if source.eof():
            raise StopIteration

        if source.test(self.line_comment):
            source.drop_while(lambda c: c != '\n')
            return self.__next__()
        if source.test(self.block_comment_start):
            source.drop(len(self.block_comment_start))
            while not source.eof() and not source.test(self.block_comment_end):
                source.drop(1)
            return self.__next__()

        cc = self.catcodes[source.current]
        if cc == CatCode.IGNORE:
            source.drop(1)
            return self.__next__()

        elif cc == CatCode.INVALID:
            raise SyntaxError("invalid character in input stream: {}/'{}'".format(
                hex(ord(source.current)), source.current
            ))

        elif cc == CatCode.LINE_COMMENT:
            source.drop_while(lambda c: c != '\n')
            return self.__next__()

        elif cc == CatCode.WHITESPACE:
            source.drop_while(lambda c: self.catcodes[c] == CatCode.WHITESPACE)
            return self.__next__()

        # if + and - are just regular names (e.g., as in Clojure), we still want to parse numbers correctly
        elif source.current in ['+', '-'] and '0' <= source.peek(1) <= '9':
            sign = source.next()
            number = self.read_number()
            if sign == '-':
                number = -number
            return pos, TokenType.NUMBER, number

        elif self.catcodes[source.peek(1)] == CatCode.STRING_DELIMITER and source.current in self.string_prefix:
            prefix = source.next()
            return pos, TokenType.STRING, prefix + self.read_string()

        elif cc == CatCode.STRING_DELIMITER:
            return pos, TokenType.STRING, self.read_string()

        elif cc in [CatCode.SYMBOL, CatCode.DELIMITER]:
            return pos, TokenType.SYMBOL, self.read_symbol()

        elif cc in [CatCode.LEFT_BRACKET, CatCode.RIGHT_BRACKET]:
            tt = TokenType.LEFT_BRACKET if cc == CatCode.LEFT_BRACKET else TokenType.RIGHT_BRACKET
            return pos, tt, source.next()

        elif '0' <= source.current <= '9' or cc == CatCode.NUMERIC:
            return pos, TokenType.NUMBER, self.read_number()

        elif cc == CatCode.ALPHA:
            name = self.read_name()
            if self.catcodes[source.current] == CatCode.STRING_DELIMITER and name in self.string_prefix:
                return pos, TokenType.STRING, name + self.read_string()
            elif name in self.constants:
                return pos, TokenType.VALUE, self.constants[name]
            else:
                tt = TokenType.KEYWORD if name in self.keywords else TokenType.SYMBOL
                return pos, tt, name

        elif cc == CatCode.NEWLINE:
            return pos, TokenType.NEWLINE, source.next()

        elif cc == CatCode.ESCAPE:
            result = self.read_escape()
            if result is None:
                return self.__next__()
            elif type(result) is tuple and len(result) == 2:
                return pos, result[0], result[1]
            else:
                return pos, TokenType.SYMBOL, result

        elif cc == CatCode.PREFIX:
            char = source.current
            result = source.take_while(lambda c: c == char)
            result += source.take_while(lambda c: self.catcodes[c] in [CatCode.ALPHA, CatCode.NUMERIC])
            return pos, TokenType.SYMBOL, result

        else:
            raise SyntaxError("invalid character in input stream: {}/'{}'".format(
                hex(ord(source.current)), source.current
            ))

    def read_escape(self):
        escapes = self.escapes.keys()
        source = self.source
        i = 0
        keys = []
        while i < source.remaining and len(escapes) > 0:
            c = source.peek(i)
            escapes = [e[1:] for e in escapes if e.startswith(c)]
            if '' in escapes:
                keys.append(source.peek_string(i))
                escapes.remove('')
            i += 1
        if len(keys) > 0:
            key = keys[-1]
            source.drop(len(key))
            return self.escapes[key]
        else:
            return self.source.next()

    def read_name(self):
        source = self.source
        return source.take_while(lambda c: self.catcodes[c] in [CatCode.ALPHA, CatCode.NUMERIC])

    def read_number(self):
        source = self.source
        if source.current == '0' and source.peek(1) in ('x', 'X', 'b','B', 'o', 'O'):
            base = { 'x': 16, 'o': 8, 'b': 2 }[source.peek(1).lower()]
            if base == 16:
                is_digit = lambda c: '0' <= c <= '9' or 'A' <= c <= 'F' or 'a' <= c <= 'f'
            elif base == 8:
                is_digit = lambda c: '0' <= c <= '7'
            else:
                is_digit = lambda c: c in ('0', '1')
            source.drop(2)
            result = source.take_while(is_digit)
            return int(result, base)

        else:
            is_digit = lambda c: '0' <= c <= '9'
            result = source.take_while(is_digit)
            if source.current == '.' and is_digit(source.peek(1)):
                result += source.next()
                result += source.take_while(is_digit)

            if source.current == '.' and self.catcodes[source.peek(1)] in [CatCode.WHITESPACE, CatCode.RIGHT_BRACKET,
                                                                           CatCode.NEWLINE, CatCode.DELIMITER]:
                result += source.next() + '0'

            if source.current in ['e', 'E'] and (is_digit(source.peek(1)) or
                                                     (source.peek(1) in ['+', '-'] and is_digit(source.peek(2)))):
                result += source.next()
                if source.current in ['+', '-']:
                    result += source.next()
                result += source.take_while(is_digit)

            if all([is_digit(c) for c in result]):
                return int(result)
            else:
                return float(result)

    def read_string(self):
        source = self.source
        delimiter = source.current
        i = 1
        while source.peek(i) not in [delimiter, '\u0000']:
            i += 2 if source.peek(i) == '\\' else 1
        if source.peek(i) == delimiter:
            i += 1
        return source.take(i)

    def read_symbol(self):
        source = self.source
        result = source.next()
        nc = source.current
        pc = source.peek(1)
        if self.catcodes[nc] == CatCode.SYMBOL:
            if self.catcodes[pc] == CatCode.SYMBOL:
                s = result + nc + pc
                if s in self.ext_symbols:
                    return result + source.take(2)
            s = result + nc
            if s in self.ext_symbols:
                return result + source.next()
        return result

    def add_constant(self, name:str, value):
        self.constants[name] = value
        assert type(name) is str and name != ''

    def add_escape_sequence(self, key:str, target=None):
        self.escapes[key] = target
        assert type(key) is str

    def add_keyword(self, keyword):
        self.keywords.add(keyword)

    def add_keywords(self, *keywords):
        for keyword in keywords:
            self.add_keyword(keyword)

    def add_string_prefix(self, prefix:str):
        self.string_prefix.add(prefix)
        assert type(prefix) is str

    def add_symbol(self, symbol:str):
        self.ext_symbols.add(symbol)
        assert type(symbol) is str

    def add_symbols(self, *symbols):
        for symbol in symbols:
            self.add_symbol(symbol)

    def get_line_from_pos(self, pos):
        return self.source.get_line_from_pos(pos)

#######################################################################################################################

class BufferedIterator(object):

    def __init__(self, source):
        self.source = source
        self.head = None

    def __iter__(self):
        return self

    def __next__(self):
        result = self.next()
        if result is None:
            raise StopIteration
        else:
            return result

    def next(self):
        if self.head is not None:
            result, self.head = self.head, None
            return result
        else:
            return next(self.source, None)

    def peek(self):
        if self.head is None:
            self.head = next(self.source, None)
        return self.head

    @property
    def has_next(self):
        return self.peek() is not None
