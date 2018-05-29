#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 22. Feb 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
from typing import Optional
from .ppl_ast import *


class NodeInfo(object):

    def __init__(self, *, base=None,
                 changed_vars:Optional[set]=None,
                 cond_vars:Optional[set]=None,
                 free_vars:Optional[set]=None,
                 has_break:bool=False,
                 has_cond:bool=False,
                 has_observe:bool=False,
                 has_return:bool=False,
                 has_sample:bool=False,
                 has_side_effects:bool=False,
                 return_count:int=0):

        if changed_vars is None:
            changed_vars = set()
        if cond_vars is None:
            cond_vars = set()
        if free_vars is None:
            free_vars = set()

        if base is None:
            bases = []
        elif isinstance(base, NodeInfo):
            bases = [base]
        elif type(base) in (list, set, tuple) and all([item is None or isinstance(item, NodeInfo) for item in base]):
            bases = [item for item in base if item is not None]
        else:
            raise TypeError("NodeInfo(): wrong type of 'base': '{}'".format(type(base)))

        self.changed_var_count = { k: 1 for k in changed_vars }   # type:dict
        self.changed_vars = changed_vars            # type:set
        self.cond_vars = cond_vars                  # type:set
        self.free_vars = free_vars                  # type:set
        self.has_break = has_break                  # type:bool
        self.has_cond = has_cond                    # type:bool
        self.has_observe = has_observe              # type:bool
        self.has_return = has_return                # type:bool
        self.has_sample = has_sample                # type:bool
        self.has_side_effects = has_side_effects    # type:bool
        self.return_count = return_count            # type:int
        for item in bases:
            self.changed_vars = set.union(self.changed_vars, item.changed_vars)
            self.cond_vars = set.union(self.cond_vars, item.cond_vars)
            self.free_vars = set.union(self.free_vars, item.free_vars)
            self.has_cond = self.has_cond or item.has_cond
            self.has_observe = self.has_observe or item.has_observe
            self.has_return = self.has_return or item.has_return
            self.has_sample = self.has_sample or item.has_sample
            self.has_side_effects = self.has_side_effects or item.has_side_effects
            self.return_count += item.return_count
            for key in item.changed_var_count:
                if key not in self.changed_var_count:
                    self.changed_var_count[key] = 0
                self.changed_var_count[key] += item.changed_var_count[key]

        self.has_changed_vars = len(self.changed_vars) > 0
        self.has_free_vars = len(self.free_vars) > 0
        self.can_embed = not (self.has_observe or self.has_sample or self.has_side_effects or self.has_changed_vars)
        self.mutable_vars = set([key for key in self.changed_var_count if self.changed_var_count[key] > 1])

        assert type(self.changed_vars) is set and all([type(item) is str for item in self.changed_vars])
        assert type(self.free_vars) is set and all([type(item) is str for item in self.free_vars])
        assert type(self.changed_var_count) is dict
        assert type(self.cond_vars) is set and all([type(item) is str for item in self.cond_vars]), cond_vars
        assert type(self.has_break) is bool
        assert type(self.has_cond) is bool
        assert type(self.has_observe) is bool
        assert type(self.has_return) is bool
        assert type(self.has_sample) is bool
        assert type(self.has_side_effects) is bool
        assert type(self.return_count) is int


    def clone(self, binding_vars:Optional[set]=None, **kwargs):
        result = NodeInfo(base=self)
        for key in kwargs:
            setattr(result, key, kwargs[key])
        if binding_vars is not None:
            result.changed_vars = set.difference(result.changed_vars, binding_vars)
            result.cond_vars = set.difference(result.cond_vars, binding_vars)
            result.free_vars = set.difference(result.free_vars, binding_vars)
            for n in binding_vars:
                if n in result.changed_var_count:
                    del result.changed_var_count[n]
        return result


    def bind_var(self, name):
        if type(name) is str:
            return self.clone(binding_vars={name})

        elif type(name) in (list, set, tuple) and all([type(item) is str for item in name]):
            return self.clone(binding_vars=set(name))

        elif name is not None:
            raise TypeError("NodeInfo(): cannot bind '{}'".format(name))

        else:
            return self


    def change_var(self, name):
        if type(name) is str:
            name = {name}

        elif type(name) in (list, set, tuple) and all([type(item) is str for item in name]):
            name = set(name)

        elif name is not None:
            raise TypeError("NodeInfo(): cannot add var-name '{}'".format(name))

        if self.has_cond:
            return NodeInfo(base=self, changed_vars=name, has_side_effects=True, cond_vars=name)
        else:
            return NodeInfo(base=self, changed_vars=name, has_side_effects=True)


    def union(self, *other):
        other = [item for item in other if item is not None]
        if len(other) == 0:
            return self
        elif all([isinstance(item, NodeInfo) for item in other]):
            return NodeInfo(base=[self] + other)
        else:
            raise TypeError("NodeInfo(): cannot build union with '{}'"
                            .format([item for item in other if not isinstance(item, NodeInfo)]))

    def is_independent(self, other):
        assert isinstance(other, NodeInfo)
        a = set.intersection(self.free_vars, other.changed_vars)
        b = set.intersection(self.changed_vars, other.free_vars)
        c = set.intersection(self.changed_vars, other.changed_vars)
        return len(a) == len(b) == len(c) == 0


class InfoAnnotator(Visitor):

    def visit_node(self, node:AstNode):
        return NodeInfo()

    def visit_attribute(self, node: AstAttribute):
        return NodeInfo(base=self.visit(node.base), free_vars={node.attr})

    def visit_binary(self, node: AstBinary):
        return NodeInfo(base=(self.visit(node.left), self.visit(node.right)))

    def visit_body(self, node: AstBody):
        return NodeInfo(base=[self.visit(item) for item in node.items])

    def visit_break(self, _):
        return NodeInfo(has_break=True)

    def visit_call(self, node: AstCall):
        base = [self.visit(node.function)]
        args = [self.visit(arg) for arg in node.args]
        return NodeInfo(base=base + args)

    def visit_compare(self, node: AstCompare):
        return NodeInfo(base=[self.visit(node.left), self.visit(node.right), self.visit(node.second_right)])

    def visit_def(self, node: AstDef):
        result = self.visit(node.value)
        return result.change_var(node.name)

    def visit_dict(self, node: AstDict):
        return NodeInfo(base=[self.visit(node.items[key]) for key in node.items])

    def visit_for(self, node: AstFor):
        source = self.visit(node.source)
        body = self.visit(node.body).bind_var(node.target)
        return NodeInfo(base=[body, source])

    def visit_function(self, node: AstFunction):
        body = self.visit(node.body)
        return body.bind_var(node.parameters).bind_var(node.vararg)

    def visit_if(self, node: AstIf):
        if node.has_else:
            base = [self.visit(node.if_node), self.visit(node.else_node)]
        else:
            base = [self.visit(node.if_node)]
        cond_vars = set.union(*[item.changed_vars for item in base])
        return NodeInfo(base=base + [self.visit(node.test)], cond_vars=cond_vars, has_cond=True)

    def visit_import(self, _):
        return NodeInfo()

    def visit_let(self, node: AstLet):
        result = self.visit(node.body).bind_var(node.target)
        result = result.union(self.visit(node.source))
        return result

    def visit_list_for(self, node: AstListFor):
        source = self.visit(node.source)
        expr = self.visit(node.expr).bind_var(node.target)
        return NodeInfo(base=[expr, source])

    def visit_observe(self, node: AstObserve):
        return NodeInfo(base=[self.visit(node.dist), self.visit(node.value)], has_observe=True)

    def visit_return(self, node: AstReturn):
        return NodeInfo(base=self.visit(node.value), has_return=True, return_count=1)

    def visit_sample(self, node: AstSample):
        return NodeInfo(base=self.visit(node.dist), has_sample=True)

    def visit_slice(self, node: AstSlice):
        base = [self.visit(node.base),
                self.visit(node.start),
                self.visit(node.stop)]
        return NodeInfo(base=base)

    def visit_subscript(self, node: AstSubscript):
        base = [self.visit(node.base), self.visit(node.index)]
        return NodeInfo(base=base)

    def visit_symbol(self, node: AstSymbol):
        return NodeInfo(free_vars={node.name})

    def visit_unary(self, node: AstUnary):
        return self.visit(node.item)

    def visit_value(self, _):
        return NodeInfo()

    def visit_value_vector(self, _):
        return NodeInfo()

    def visit_vector(self, node: AstVector):
        return NodeInfo(base=[self.visit(item) for item in node.items])

    def visit_while(self, node: AstWhile):
        base = [self.visit(node.test), self.visit(node.body)]
        return NodeInfo(base=base, has_side_effects=True)


class VarCountVisitor(Visitor):

    __visit_children_first__ = True

    def __init__(self, name:str):
        super().__init__()
        self.count = 0
        self.name = name
        assert type(self.name) is str and self.name != ''

    def visit_node(self, node:AstNode):
        return node

    def visit_symbol(self, node:AstSymbol):
        if node.name == self.name:
            self.count += 1
        return node



def get_info(ast:AstNode) -> NodeInfo:
    return InfoAnnotator().visit(ast)

def count_variable_usage(name:str, ast:AstNode):
    vcv = VarCountVisitor(name)
    vcv.visit(ast)
    return vcv.count