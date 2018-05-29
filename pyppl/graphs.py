#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Dec 2017, Tobias Kohn
# 11. May 2018, Tobias Kohn
#
from typing import Optional
from . import distributions


class GraphNode(object):
    """
    The base class for all nodes, including the actual graph vertices, but also conditionals, data, and possibly
    parameters.

    Each node has a name, which is usually generated automatically. The generation of the name is based on a simple
    counter. This generated name (i.e. the counter value inside the name) is used later on to impose a compute order
    on the nodes (see the method `get_ordered_list_of_all_nodes` in the `graph`). Hence, you should not change the
    naming scheme unless you know exactly what you are doing!

    The set of ancestors provides the edges for the graph and the graphical model, respectively. Note that all
    ancestors are always vertices. Conditions, parameters, data, etc. are hold in other fields. This ensures that by
    looking at the ancestors of vertices, we get the pure graphical model.

    Finally, the methods `evaluate`, `update` and `update_pdf` are used by the model to sample values and compute
    log-pdf, etc. Of course, `evaluate` is just a placeholder here so as to define a minimal interface. Usually, you
    will use `update` and `update_pdf` instead of `evaluate`. However, given a `state`-dictionary holding all the
    necessary values, it is save to call `evaluate`.
    """

    def __init__(self, name: str, ancestors: Optional[set]=None):
        if ancestors is None:
            ancestors = set()
        self.ancestors = ancestors
        self.name = name
        self.original_name = name
        assert type(self.ancestors) is set
        assert type(self.name) is str
        assert all([isinstance(item, GraphNode) for item in self.ancestors])

    @property
    def display_name(self):
        if hasattr(self, 'original_name'):
            name = self.original_name
            if name is not None and '.' in name:
                name = name.split('.')[-1]
            if name is not None and len(name) > 0:
                return name.replace('_', '')
        return self.name[-3:]

    def create_repr(self, caption: str, **fields):

        def fmt_field(key):
            value = fields[key]
            if value is None:
                return '-'
            elif type(value) in (list, set, tuple) and all([isinstance(item, GraphNode) for item in value]):
                return ', '.join([item.name for item in value])
            elif type(value) in (list, set, tuple) and \
                all([type(item) is tuple and isinstance(item[0], GraphNode) for item in value]):
                return ', '.join(['{}={}'.format(item[0].name, item[1]) for item in value])
            else:
                return value

        if len(fields) > 0:
            key_len = max(max([len(key) for key in fields]), 9)
            fmt = "  {:" + str(key_len+2) + "}{}"
            result = [fmt.format(key+':', fmt_field(key)) for key in fields if fields[key] is not None]
        else:
            fmt = "  {:11}{}"
            result = []
        result.insert(0, fmt.format("Ancestors:", ', '.join([item.name for item in self.ancestors])))
        result.insert(0, fmt.format("Name:", self.name))
        line_no = getattr(self, 'line_number', -1)
        if line_no > 0:
            result.append(fmt.format("Line:", line_no))
        return "{}\n{}".format(caption, '\n'.join(result))

    def __repr__(self):
        return self.create_repr(self.name)

    def get_code(self):
        raise NotImplemented


####################################################################################################

class ConditionNode(GraphNode):
    """
    A `ConditionNode` represents a condition that depends on stochastic variables (vertices). It is not directly
    part of the graphical model, but you can think of conditions to be attached to a specific vertex.

    Usually, we try to transform all conditions into the form `f(state) >= 0` (this is not possible for `f(X) == 0`,
    through). However, if the condition satisfies this format, the node object has an associated `function`, which
    can be evaluated on its own. In other words: you can not only check if a condition is `True` or `False`, but you
    can also gain information about the 'distance' to the 'border'.
    """

    __condition_node_counter = 1

    def __init__(self, name: str, *, ancestors: Optional[set]=None,
                 condition: str,
                 function: Optional[str]=None,
                 op: Optional[str]=None,
                 compare_value: Optional[float]=None):
        super().__init__(name, ancestors)
        self.condition = condition
        self.function = function
        self.op = op
        self.compare_value = compare_value
        self.bit_index = self.__class__.__condition_node_counter
        self.__class__.__condition_node_counter *= 2
        for a in ancestors:
            if isinstance(a, Vertex):
                a.add_dependent_condition(self)

    def __repr__(self):
        return self.create_repr("Condition", Condition=self.condition, Function=self.function, Op=self.op,
                                CompareValue=self.compare_value)

    def get_code(self):
        return self.condition

    def is_false_from_bit_vector(self, bit_vector):
        return (bit_vector & self.bit_index) == 0

    def is_true_from_bit_vector(self, bit_vector):
        return (bit_vector & self.bit_index) > 0

    def update_bit_vector(self, state, bit_vector):
        if state[self.name] is True:
            bit_vector |= self.bit_index
        return bit_vector


class DataNode(GraphNode):
    """
    Data nodes do not carry out any computation, but provide the data. They are used to keep larger data set out
    of the code, as large lists are replaced by symbols.
    """

    def __init__(self, name: str, *, ancestors: Optional[set]=None, data: str):
        super().__init__(name, ancestors)
        self.data_code = data

    def __repr__(self):
        return self.create_repr("Data", Data=self.data_code)

    def get_code(self):
        return self.data_code


class Vertex(GraphNode):
    """
    Vertices play the crucial and central role in the graphical model. Each vertex represents either the sampling from
    a distribution, or the observation of such a sampled value.

    You can get the entire graphical model by taking the set of vertices and their `ancestors`-fields, containing all
    vertices, upon which this vertex depends. However, there is a plethora of additional fields, providing information
    about the node and its relationship and status.

    `name`:
      The generated name of the vertex. See also: `original_name`.
    `original_name`:
      In contrast to the `name`-field, this field either contains the name attributed to this value in the original
      code, or `None`.
    `ancestors`:
      The set of all parent vertices. This contains only the ancestors, which are in direct line, and not the parents
      of parents. Use the `get_all_ancestors()`-method to retrieve a full list of all ancestors (including parents of
      parents of parents of ...).
    `dist_ancestors`:
      The set of ancestors used for the distribution/sampling, without those used inside the conditions.
    `cond_ancestors`:
      The set of ancestors, which are linked through conditionals.
    `distribution_name`:
      The name of the distribution, such as `Normal` or `Gamma`.
    `distribution_type`:
      Either `"continuous"` or `"discrete"`. You will usually query this field using one of the properties
      `is_continuous` or `is_discrete`.
    `observation`:
      The observation as a string containing Python-code.
    `conditions`:
      The set of all conditions under which this vertex is evaluated. Each item in the set is actually a tuple of
      a `ConditionNode` and a boolean value, to which the condition should evaluate. Note that the conditions are
      not owned by a vertex, but might be shared across several vertices.
    `dependent_conditions`:
      The set of all conditions that depend on this vertex. In other words, all conditions which contain this
      vertex in their `get_all_ancestors`-set.
    `sample_size`:
      The dimension of the samples drawn from this distribution.
    """

    def __init__(self, name: str, *,
                 ancestors: Optional[set]=None,
                 condition_nodes: Optional[set]=None,
                 conditions: Optional[set]=None,
                 distribution_args: Optional[list]=None,
                 distribution_arg_names: Optional[list]=None,
                 distribution_code: str,
                 distribution_func: Optional[str]=None,
                 distribution_name: str,
                 distribution_transform=None,
                 observation: Optional[str]=None,
                 observation_value: Optional=None,
                 original_name: Optional[str]=None,
                 sample_size: int = 1,
                 line_number: int = -1):
        super().__init__(name, ancestors)
        self.condition_nodes = condition_nodes
        self.conditions = conditions
        self.distribution_args = distribution_args
        self.distribution_arg_names = distribution_arg_names
        self.distribution_code = distribution_code
        self.distribution_func = distribution_func
        self.distribution_name = distribution_name
        distr = distributions.get_distribution_for_name(distribution_name)
        self.distribution_type = distr.distribution_type if distr is not None else None
        self.distribution_transform = distribution_transform
        self.observation = observation
        self.observation_value = observation_value
        self.original_name = original_name
        self.line_number = line_number
        self.sample_size = sample_size
        self.dependent_conditions = set()
        if conditions is not None:
            if self.condition_nodes is None:
                self.condition_nodes = set()
            for cond, truth_value in conditions:
                self.condition_nodes.add(cond)
        self.condition_ancestors = set()
        if self.condition_nodes is not None:
            for cond in self.condition_nodes:
                self.condition_ancestors = set.union(self.condition_ancestors, cond.ancestors)
        if self.distribution_args is not None and self.distribution_arg_names is not None and \
            len(self.distribution_args) == len(self.distribution_arg_names):
            self.distribution_arguments = { n: v for n, v in zip(self.distribution_arg_names, self.distribution_args) }
        else:
            self.distribution_arguments = None

    def __repr__(self):
        args = {
            "Conditions":  self.conditions,
            "Cond-Ancs.":  self.condition_ancestors,
            "Cond-Nodes":  self.condition_nodes,
            "Dist-Args":   self.distribution_arguments,
            "Dist-Code":   self.distribution_code,
            "Dist-Name":   self.distribution_name,
            "Dist-Type":   self.distribution_type,
            "Dist-Transform": self.distribution_transform,
            "Sample-Size": self.sample_size,
            "Orig. Name":  self.original_name,
        }
        if self.observation is not None:
            args["Observation"] = self.observation
        title = "Observe" if self.observation is not None else "Sample"
        return self.create_repr("Vertex {} [{}]".format(self.name, title), **args)

    def get_code(self, **flags):
        if self.distribution_func is not None and self.distribution_args is not None:
            args = self.distribution_args[:]
            if self.distribution_arg_names is not None:
                arg_names = self.distribution_arg_names
                if len(arg_names) < len(args):
                    arg_names = ['{}='.format(n) for n in arg_names]
                    arg_names = [''] * (len(args)-len(arg_names)) + arg_names
                    args = ["{}{}".format(a, b) for a, b in zip(arg_names, args) if a not in flags.keys()]
                else:
                    args = ["{}={}".format(a, b) for a, b in zip(arg_names, args) if a not in flags.keys()]
            for key in flags:
                args.append("{}={}".format(key, flags[key]))
            return "{}({})".format(self.distribution_func, ', '.join(args))
        return self.distribution_code

    def get_cond_code(self, state_object: Optional[str]=None):
        if self.conditions is not None and len(self.conditions) > 0:
            result = []
            for cond, truth_value in self.conditions:
                name = cond.name
                if state_object is not None:
                    name = "{}['{}']".format(state_object, name)
                if truth_value:
                    result.append(name)
                else:
                    result.append('not ' + name)
            return "if {}:\n\t".format(' and '.join(result))
        else:
            return None

    def add_dependent_condition(self, cond: ConditionNode):
        self.dependent_conditions.add(cond)
        for a in self.ancestors:
            a.add_dependent_condition(cond)

    @property
    def has_observation(self):
        return self.observation is not None

    @property
    def get_all_ancestors(self):
        result = []
        for a in self.ancestors:
            if a not in result:
                result.append(a)
                result += list(a.get_all_ancestors())
        return set(result)

    @property
    def is_conditional(self):
        return len(self.dependent_conditions) > 0

    @property
    def is_continuous(self):
        return self.distribution_type == distributions.DistributionType.CONTINUOUS

    @property
    def is_discrete(self):
        return self.distribution_type == distributions.DistributionType.DISCRETE

    @property
    def is_observed(self):
        return self.observation is not None

    @property
    def is_sampled(self):
        return self.observation is None

    @property
    def has_conditions(self):
        return self.conditions is not None and len(self.conditions) > 0
