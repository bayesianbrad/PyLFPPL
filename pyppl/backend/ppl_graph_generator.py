#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 12. Mar 2018, Tobias Kohn
# 23. Mar 2018, Tobias Kohn
#
from ..ppl_ast import *
from ..graphs import *
from .ppl_graph_factory import GraphFactory


class ConditionScope(object):

    def __init__(self, prev, condition):
        self.prev = prev
        self.condition = condition
        self.truth_value = True

    def switch_branch(self):
        self.truth_value = not self.truth_value

    def get_condition(self):
        return (self.condition, self.truth_value)


class ConditionScopeContext(object):

    def __init__(self, visitor):
        self.visitor = visitor

    def __enter__(self):
        return self.visitor.conditions

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.visitor.leave_condition()


class GraphGenerator(ScopedVisitor):

    def __init__(self, factory: Optional[GraphFactory]=None):
        super().__init__()
        if factory is None:
            factory = GraphFactory()
        self.factory = factory
        self.nodes = []
        self.conditions = None  # type: ConditionScope
        self.imports = set()

    def enter_condition(self, condition):
        self.conditions = ConditionScope(self.conditions, condition)

    def leave_condition(self):
        self.conditions = self.conditions.prev

    def switch_condition(self):
        self.conditions.switch_branch()

    def create_condition(self, condition):
        self.enter_condition(condition)
        return ConditionScopeContext(self)

    def get_current_conditions(self):
        result = []
        c = self.conditions
        while c is not None:
            result.append(c.get_condition())
            c = c.prev
        return set(result)

    def _visit_dict(self, items):
        result = {}
        parents = set()
        for key in items.keys():
            item, parent = self.visit(items[key])
            result[key] = item
            parents = set.union(parents, parent)
        return result, parents

    def _visit_items(self, items):
        result = []
        parents = set()
        for _item in (self.visit(item) for item in items):
            if _item is not None:
                item, parent = _item
                result.append(item)
                parents = set.union(parents, parent)
            else:
                result.append(None)
        return result, parents

    def visit_node(self, node: AstNode):
        raise RuntimeError("cannot compile '{}'".format(node))

    def visit_attribute(self, node:AstAttribute):
        base, parents = self.visit(node.base)
        if base is node.base:
            return node, parents
        else:
            return AstAttribute(base, node.attr), parents

    def visit_binary(self, node:AstBinary):
        left, l_parents = self.visit(node.left)
        right, r_parents = self.visit(node.right)
        return AstBinary(left, node.op, right), set.union(l_parents, r_parents)

    def visit_body(self, node:AstBody):
        items, parents = self._visit_items(node.items)
        return makeBody(items), parents

    def visit_call(self, node: AstCall):
        function, f_parents = self.visit(node.function)
        args, a_parents = self._visit_items(node.args)
        parents = set.union(f_parents, a_parents)
        return AstCall(function, args, node.keywords), parents

    def visit_call_torch_function(self, node: AstCall):
        name = node.function_name
        if name.startswith("torch.") and node.arg_count == 1 and isinstance(node.args[0], AstValueVector):
            name = name[6:]
            if name in ('tensor', 'Tensor', 'FloatTensor', 'IntTensor', 'DoubleTensor', 'HalfTensor',
                        'ByteTensor', 'ShortTensor', 'LongTensor'):
                node = self.factory.create_data_node(node)
                if node is not None:
                    self.nodes.append(node)
                    return AstSymbol(node.name, node=node), set()

        elif name.startswith('torch.') and name[6:] in ('eq', 'ge', 'gt', 'le', 'lt', 'ne') and node.arg_count == 2:
            left, l_parents = self.visit(node.left)
            right, r_parents = self.visit(node.right)
            parents = set.union(l_parents, r_parents)
            cond_node = self.factory.create_condition_node(node.clone(args=[left, right]), parents)
            if cond_node is not None:
                self.nodes.append(cond_node)
                name = cond_node.name
                return AstSymbol(name, node=cond_node), parents

        return self.visit_call(node)

    def visit_compare(self, node: AstCompare):
        left, l_parents = self.visit(node.left)
        right, r_parents = self.visit(node.right)
        if node.second_right is not None:
            second_right, sc_parents = self.visit(node.second_right)
            parents = set.union(l_parents, r_parents)
            parents = set.union(parents, sc_parents)
            return AstCompare(left, node.op, right, node.second_op, second_right), parents
        else:
            return AstCompare(left, node.op, right), set.union(l_parents, r_parents)

    def visit_def(self, node: AstDef):
        self.define(node.name, self.visit(node.value))
        return AstValue(None), set()

    def visit_dict(self, node: AstDict):
        items, parents = self._visit_dict(node.items)
        return AstDict(items), parents

    def visit_for(self, node: AstFor):
        source, s_parents = self.visit(node.source)
        body, b_parents = self.visit(node.body)
        parents = set.union(s_parents, b_parents)
        return AstFor(node.target, source, body), parents

    def visit_if(self, node: AstIf):
        test, parents = self.visit(node.test)
        cond_node = self.factory.create_condition_node(test, parents)
        if cond_node is not None:
            self.nodes.append(cond_node)
            name = cond_node.name
            test = AstSymbol(name, node=cond_node)

        with self.create_condition(cond_node):
            a_node, a_parents = self.visit(node.if_node)
            parents = set.union(parents, a_parents)
            self.switch_condition()
            b_node, b_parents = self.visit(node.else_node)
            parents = set.union(parents, b_parents)

        return AstIf(test, a_node, b_node), parents

    def visit_import(self, node: AstImport):
        self.imports.add(node.module_name)
        return AstValue(None), set()

    def visit_let(self, node: AstLet):
        self.define(node.target, self.visit(node.source))
        return self.visit(node.body)

    def visit_list_for(self, node: AstListFor):
        source, s_parents = self.visit(node.source)
        expr, e_parents = self.visit(node.expr)
        parents = set.union(s_parents, e_parents)
        if node.test is not None:
            test, t_parents = self.visit(node.test)
            parents = set.union(parents, t_parents)
        else:
            test = None
        return AstListFor(node.target, source, expr, test), parents

    def visit_multi_slice(self, node: AstMultiSlice):
        items, parents = self._visit_items(node.indices)
        result = node.clone(indices=items)
        return result, parents

    def visit_observe(self, node: AstObserve):
        dist, d_parents = self.visit(node.dist)
        value, v_parents = self.visit(node.value)
        parents = set.union(d_parents, v_parents)
        node = self.factory.create_observe_node(dist, value, parents, self.get_current_conditions())
        self.nodes.append(node)
        return AstSymbol(node.name, node=node), set()

    def visit_sample(self, node: AstSample):
        dist, d_parents = self.visit(node.dist)
        if node.size is not None:
            size, s_parents = self.visit(node.size)
            parents = set.union(d_parents, s_parents)
            if isinstance(size, AstValue):
                size = size.value
            else:
                raise RuntimeError("sample size must be a constant integer value instead of '{}'".format(size))
        else:
            size = 1
            parents = d_parents
        node = self.factory.create_sample_node(dist, size, parents, original_name=getattr(node, 'original_name', None))
        self.nodes.append(node)
        return AstSymbol(node.name, node=node), { node }

    def visit_slice(self, node: AstSlice):
        base, parents = self.visit(node.base)
        if node.start is not None:
            start, a_parents = self.visit(node.start)
            parents = set.union(parents, a_parents)
        else:
            start = None
        if node.stop is not None:
            stop, a_parents = self.visit(node.stop)
            parents = set.union(parents, a_parents)
        else:
            stop = None
        return AstSlice(base, start, stop), parents

    def visit_subscript(self, node: AstSubscript):
        base, b_parents = self.visit(node.base)
        index, i_parents = self.visit(node.index)
        if is_vector(base) and is_integer(index):
            return self.visit(base[index.value])
        return makeSubscript(base, index), set.union(b_parents, i_parents)

    def visit_symbol(self, node: AstSymbol):
        item = self.resolve(node.name)
        if item is not None:
            return item
        elif node.node is not None:
            return node, { node.node }
        elif node.predef:
            return node, set()
        else:
            line = " [line {}]".format(node.lineno) if hasattr(node, 'lineno') else ''
            raise RuntimeError("symbol not found: '{}'{}".format(node.original_name, line))

    def visit_unary(self, node: AstUnary):
        item, parents = self.visit(node.item)
        return AstUnary(node.op, item), parents

    def visit_value(self, node: AstValue):
        return node, set()

    def visit_value_vector(self, node: AstValueVector):
        if len(node) > 3:
            node = self.factory.create_data_node(node)
            if node is not None:
                self.nodes.append(node)
                return AstSymbol(node.name, node=node), set()
        return node, set()

    def visit_vector(self, node: AstVector):
        items, parents = self._visit_items(node.items)
        result = makeVector(items)
        return result, parents

    def generate_code(self, imports: Optional[str]=None, *,
                      base_class: Optional[str]=None,
                      class_name: Optional[str]=None):
        if len(self.imports) > 0:
            _imports = '\n'.join(['import {}'.format(item) for item in self.imports])
            if imports is not None:
                _imports += '\n' + imports
        elif imports is not None:
            _imports = imports
        else:
            _imports = ''
        return self.factory.generate_code(class_name=class_name, imports=_imports,
                                          base_class=base_class)

    def generate_model(self, imports: Optional[str]=None, base_class: Optional[str]=None, class_name: str='Model'):
        vertices = set()
        arcs = set()
        data = set()
        conditionals = set()
        for node in self.nodes:
            if isinstance(node, Vertex):
                vertices.add(node)
                for a in node.ancestors:
                    arcs.add((a, node))
            elif isinstance(node, DataNode):
                data.add(node)
            elif isinstance(node, ConditionNode):
                conditionals.add(node)

        code = self.generate_code(imports=imports, base_class=base_class, class_name=class_name)
        c_globals = {}
        exec(code, c_globals)
        Model = c_globals[class_name]
        result = Model(vertices, arcs, data, conditionals)
        result.code = code
        return result
