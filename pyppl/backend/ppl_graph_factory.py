#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 12. Mar 2018, Tobias Kohn
# 11. May 2018, Tobias Kohn
#
from ..ppl_ast import *
from ..graphs import *
from .ppl_code_generator import CodeGenerator
from .ppl_graph_codegen import GraphCodeGenerator
from .. import distributions


class _ConditionCollector(Visitor):

    __visit_children_first__ = True

    def __init__(self):
        super().__init__()
        self.cond_nodes = set()

    def visit_symbol(self, node: AstSymbol):
        if isinstance(node.node, ConditionNode):
            self.cond_nodes.add(node.node)
        return self.visit_node(node)


class GraphFactory(object):

    def __init__(self, code_generator=None):
        if code_generator is None:
            code_generator = CodeGenerator()
            code_generator.state_object = 'state'
        self._counter = 30000
        self.nodes = []
        self.code_generator = code_generator
        self.cond_nodes_map = {}
        self.data_nodes_cache = {}

    def _generate_code_for_node(self, node: AstNode):
        return self.code_generator.visit(node)

    def generate_symbol(self, prefix: str):
        self._counter += 1
        return prefix + str(self._counter)

    def create_node(self, parents: set):
        assert type(parents) is set
        return None

    def create_condition_node(self, test: AstNode, parents: set):
        name = self.generate_symbol('cond_')
        code = self._generate_code_for_node(test)
        if code in self.cond_nodes_map:
            return self.cond_nodes_map[code]
        if isinstance(test, AstCompare) and is_zero(test.right) and test.second_right is None:
            result = ConditionNode(name, ancestors=parents, condition=code,
                                   function=self._generate_code_for_node(test.left), op=test.op)
        elif isinstance(test, AstCall) and test.function_name.startswith('torch.') and is_number(test.right):
            result = ConditionNode(name, ancestors=parents, condition=code,
                                   function=self._generate_code_for_node(test.left), op=test.function_name,
                                   compare_value=test.right.value)
        else:
            result = ConditionNode(name, ancestors=parents, condition=code)
        self.nodes.append(result)
        self.cond_nodes_map[code] = result
        return result

    def create_data_node(self, data: AstNode, parents: Optional[set]=None):
        if parents is None:
            parents = set()
        code = self._generate_code_for_node(data)
        if code in self.data_nodes_cache:
            return self.data_nodes_cache[code]
        name = self.generate_symbol('data_')
        result = DataNode(name, ancestors=parents, data=code)
        self.nodes.append(result)
        self.data_nodes_cache[code] = result
        return result

    def create_observe_node(self, dist: AstNode, value: AstNode, parents: set, conditions: set):
        arg_names = None
        if isinstance(dist, AstCall):
            func = dist.function_name
            args = [self._generate_code_for_node(arg) for arg in dist.args]
            # args = dist.add_keywords_to_args(args)
            trans = dist.get_keyword_arg_value("transform")
            distr = distributions.get_distribution_for_name(func)
            if distr is not None:
                if 0 < dist.pos_arg_count <= len(distr.params):
                    arg_names = distr.params[:dist.pos_arg_count] + dist.keywords
        else:
            func = None
            args = None
            trans = None
        name = self.generate_symbol('y')
        d_code = self._generate_code_for_node(dist)
        v_code = self._generate_code_for_node(value)
        obs_value = value.value if is_value(value) else None
        cc = _ConditionCollector()
        cc.visit(dist)
        result = Vertex(name, ancestors=parents, distribution_code=d_code, distribution_name=_get_dist_name(dist),
                        distribution_args=args, distribution_func=func,
                        distribution_transform=trans, distribution_arg_names=arg_names,
                        observation=v_code,
                        observation_value=obs_value, conditions=conditions,
                        condition_nodes=cc.cond_nodes if len(cc.cond_nodes) > 0 else None)
        self.nodes.append(result)
        return result

    def create_sample_node(self, dist: AstNode, size: int, parents: set, original_name: Optional[str]=None):
        arg_names = None
        if isinstance(dist, AstCall):
            func = dist.function_name
            args = [self._generate_code_for_node(arg) for arg in dist.args]
            # args = dist.add_keywords_to_args(args)
            trans = dist.get_keyword_arg_value("transform")
            distr = distributions.get_distribution_for_name(func)
            if distr is not None:
                if 0 < dist.pos_arg_count <= len(distr.params):
                    arg_names = distr.params[:dist.pos_arg_count] + dist.keywords
        else:
            func = None
            args = None
            trans = None
        name = self.generate_symbol('x')
        code = self._generate_code_for_node(dist)
        result = Vertex(name, ancestors=parents, distribution_code=code, distribution_name=_get_dist_name(dist),
                        distribution_args=args, distribution_func=func, distribution_transform=trans,
                        distribution_arg_names=arg_names,
                        sample_size=size, original_name=original_name)
        self.nodes.append(result)
        return result

    def generate_code(self, *, class_name: Optional[str] = None, imports: Optional[str]=None,
                      base_class: Optional[str]=None):
        code_gen = GraphCodeGenerator(self.nodes, self.code_generator.state_object,
                                      imports=imports if imports is not None else '')
        return code_gen.generate_model_code(class_name=class_name, base_class=base_class)


def _get_dist_name(dist: AstNode):
    if isinstance(dist, AstCall):
        result = dist.function_name
        if result.startswith('dist.'):
            result = result[5:]
        return result
    elif isinstance(dist, AstSubscript):
        if isinstance(dist.base, AstVector):
            names = set([_get_dist_name(x) for x in dist.base.items])
            if len(names) == 1:
                return tuple(names)[0]

    raise Exception("Not a valid distribution: '{}'".format(repr(dist)))
