#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 07. Mar 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
from .types import ppl_types, ppl_type_inference
from .ppl_ast import *
from .ppl_namespaces import namespace_from_module

class Symbol(object):

    def __init__(self, name:str, read_only:bool=False, missing:bool=False, predef:Optional[str]=None):
        global _symbol_counter
        self.name = name            # type:str
        self.usage_count = 0        # type:int
        self.modify_count = 0       # type:int
        self.read_only = read_only  # type:bool
        self.value_type = None
        if predef is not None:
            self.full_name = predef
            self.is_predef = True
        elif '.' in self.name:
            self.full_name = self.name
            self.is_predef = True
        else:
            self.full_name = name
            self.is_predef = False
        if missing:
            self.modify_count = -1
        assert type(self.name) is str
        assert type(self.read_only) is bool
        assert predef is None or type(predef) is str

    def use(self):
        self.usage_count += 1

    def modify(self):
        self.modify_count += 1

    def get_type(self):
        return self.value_type

    def set_type(self, tp):
        if self.value_type is not None and tp is not None:
            self.value_type = ppl_types.union(self.value_type, tp)
        elif tp is not None:
            self.value_type = tp

    def __repr__(self):
        return "{}[{}/{}{}]".format(self.full_name, self.usage_count, self.modify_count, 'R' if self.read_only else '')


class SymbolTableGenerator(ScopedVisitor):
    """
    Walks the AST and records all symbols, their definitions and usages. After walking the AST, the field `symbols`
    is a list of all symbols used in the program.

    Note that nodes of type `AstSymbol` are modified by walking the tree. In particular, the Symbol-Table-Generator
    sets the field `symbol` of `AstSymbol`-nodes and modifies the `name`-field, so that all names in the program are
    guaranteed to be unique.
    By relying on the fact that all names in the program are unique, we can later on use a flat list of symbol values
    without worrying about correct scoping (the scoping is taken care of here).
    """

    def __init__(self, namespace: Optional[dict]=None):
        super().__init__()
        if namespace is None:
            namespace = {}
        self.symbols = []
        self.current_lineno = None
        self.type_inferencer = ppl_type_inference.TypeInferencer(self)
        self.namespace = namespace

    def get_type(self, node:AstNode):
        result = self.type_inferencer.visit(node)
        return result if result is not None else ppl_types.AnyType

    def get_full_name(self, name:str):
        for sym in self.symbols:
            if sym.name == name:
                return sym.full_name
        return name

    def get_item_type(self, node:AstNode):
        tp = self.get_type(node)
        if isinstance(tp, ppl_types.SequenceType):
            return tp.item
        else:
            return ppl_types.AnyType

    def get_symbols(self):
        for symbol in self.symbols:
            if symbol.modify_count == 0:
                symbol.read_only = True
        return self.symbols

    def create_symbol(self, name:str, read_only:bool=False, missing:bool=False):
        symbol = Symbol(name, read_only=read_only, missing=missing)
        self.symbols.append(symbol)
        return symbol

    def g_def(self, name:str, read_only:bool=False, value_type=None):
        if name == '_':
            return None
        symbol = self.global_scope.resolve(name)
        if symbol is None:
            symbol = self.create_symbol(name, read_only)
            self.global_scope.define(name, symbol)
        else:
            symbol.modify()
        if symbol is not None and value_type is not None:
            symbol.set_type(value_type)
        return symbol

    def l_def(self, name:str, read_only:bool=False, value_type=None):
        if name == '_':
            return None
        symbol = self.resolve(name)
        if symbol is None:
            symbol = self.create_symbol(name, read_only)
            self.define(name, symbol)
        else:
            symbol.modify()
        if symbol is not None and value_type is not None:
            symbol.set_type(value_type)
        return symbol

    def use_symbol(self, name:str):
        if name == '_':
            return None
        symbol = self.resolve(name)
        if symbol is None:
            symbol = self.create_symbol(name, missing=True)
            self.global_scope.define(name, symbol)
        symbol.use()
        return symbol

    def import_symbol(self, name:str, full_name:str):
        symbol = Symbol(name, read_only=True, predef=full_name)
        self.define(name, symbol)
        return symbol


    def visit_node(self, node:AstNode):
        node.visit_children(self)

    def visit_def(self, node: AstDef):
        self.visit(node.value)
        sym = self.resolve(node.name)
        if sym is not None and sym.read_only:
            raise TypeError("[line {}] cannot modify '{}'".format(self.current_lineno, node.name))
        if node.global_context:
            sym = self.g_def(node.name, read_only=False, value_type=self.get_type(node.value))
        else:
            sym = self.l_def(node.name, read_only=False, value_type=self.get_type(node.value))
        if sym is not None:
            node.name = sym.full_name

    def visit_for(self, node: AstFor):
        self.visit(node.source)
        with self.create_scope():
            sym = self.l_def(node.target, read_only=True, value_type=self.get_item_type(node.source))
            if sym is not None:
                node.target = sym.full_name
            self.visit(node.body)

    def visit_function(self, node: AstFunction):
        with self.create_scope():
            for i in range(len(node.parameters)):
                param = node.parameters[i]
                sym = self.l_def(param)
                if sym is not None:
                    node.parameters[i] = sym.full_name
            if node.vararg is not None:
                sym = self.l_def(node.vararg)
                if sym is not None:
                    node.vararg = sym.full_name
            self.visit(node.body)
            node.f_locals = set(self.get_full_name(n) for n in self.scope.bindings.keys())

    def visit_import(self, node: AstImport):
        module, names = namespace_from_module(node.module_name)
        if node.imported_names is not None:
            if node.alias is None:
                for name in node.imported_names:
                    self.import_symbol(name, "{}.{}".format(module, name))
            else:
                self.import_symbol(node.alias, "{}.{}".format(module, node.imported_names[0]))

        else:
            m = node.module_name if node.alias is None else node.alias
            self.import_symbol(m, module)
            for name in names:
                self.import_symbol("{}.{}".format(m, name), "{}.{}".format(module, name))

    def visit_let(self, node: AstLet):
        self.visit(node.source)
        with self.create_scope():
            sym = self.l_def(node.target, read_only=True, value_type=self.get_type(node.source))
            if sym is not None:
                node.target = sym.full_name
            self.visit(node.body)

    def visit_list_for(self, node: AstListFor):
        self.visit(node.source)
        with self.create_scope():
            sym = self.l_def(node.target, read_only=True, value_type=self.get_item_type(node.source))
            if sym is not None:
                node.target = sym.full_name
            self.visit(node.test)
            self.visit(node.expr)

    def visit_symbol(self, node: AstSymbol):
        if node.original_name in self.namespace:
            node.name = self.namespace[node.original_name]
            node.original_name = node.name
            node.predef = True
        if not node.predef:
            symbol = self.use_symbol(node.original_name)
            node.symbol = symbol
            node.name = symbol.full_name
            if symbol.is_predef:
                node.original_name = node.name

    def visit_while(self, node: AstWhile):
        return self.visit_node(node)


def generate_symbol_table(ast):
    table_generator = SymbolTableGenerator()
    table_generator.visit(ast)
    result = table_generator.symbols
    return result
