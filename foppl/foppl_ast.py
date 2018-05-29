#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 21. Dec 2017, Tobias Kohn
# 31. Jan 2018, Tobias Kohn
#
from .graphs import *
from .foppl_objects import Symbol
from .distributions import get_distribution_for_name
# from .foppl_distributions import continuous_distributions, discrete_distributions

def _has_second_argument(f):
    try:
        if f.__code__.co_argcount < 3:
            return f.__code__.co_flags & 4 > 0
        else:
            return True
    except:
        return False


class Node(object):

    id = None
    tag = None

    def get_children(self):
        return []

    def walk(self, walker):
        name = self.__class__.__name__.lower()
        if name.startswith('ast'):
            name = name[3:]
        if name.endswith('_Node'):
            name = name[:-5]
        if hasattr(walker, 'enter_' + name) and hasattr(walker, 'leave_' + name):
            enter_method = getattr(walker, 'enter_' + name)
            leave_method = getattr(walker, 'leave_' + name)
            enter_method(self)
            results = [child.walk(walker) for child in self.get_children()]
            if _has_second_argument(leave_method):
                return leave_method(self, results)
            else:
                return leave_method(self)
        elif hasattr(walker, 'visit_' + name):
            visit_method = getattr(walker, 'visit_' + name)
            return visit_method(self)
        else:
            result = walker.visit_node(self)
            for c in self.get_children():
                if isinstance(c, Node):
                    c.walk(walker)
            return result


class Walker(object):

    def visit_node(self, node: Node):
        return node

    def walk(self, root: Node):
        if root:
            return root.walk(self)
        else:
            return None

    def walk_all(self, items: list):
        return [item.walk(self) for item in items]

###################################################################################################

class AstBinary(Node):

    def __init__(self, op: str, left: Node, right: Node):
        if isinstance(op, Symbol):
            op = op.name
        self.op = op
        self.left = left
        self.right = right

    def get_children(self):
        return [self.left, self.right]

    def __repr__(self):
        return "({} {} {})".format(repr(self.left), self.op, repr(self.right))


class AstBody(Node):

    def __init__(self, body):
        self.body = body

    def get_children(self):
        return self.body

    def __repr__(self):
        return "body({})".format('; '.join([repr(item) for item in self.body]))


class AstCompare(Node):

    def __init__(self, op: str, left: Node, right: Node):
        if isinstance(op, Symbol):
            op = op.name
        self.op = op
        self.left = left
        self.right = right

    def get_children(self):
        return [self.left, self.right]

    def __repr__(self):
        return "({} {} {})".format(repr(self.left), self.op, repr(self.right))


class AstDef(Node):

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def get_children(self):
        return [self.value]

    def __repr__(self):
        return "def({} := {})".format(self.name, repr(self.value))


class AstDistribution(Node):

    def __init__(self, name: str, args, line_number:int=-1):
        self.name = name
        self.args = args
        dist = get_distribution_for_name(name)
        if dist is not None:
            self.is_continuous = dist.is_continuous
            self.is_discrete = dist.is_discrete
        else:
            self.is_continuous = False
            self.is_discrete = False
            raise RuntimeError("???")
        if self.is_continuous or self.is_discrete and name[0].islower():
            self.name = name[0].upper() + name[1:]
        self.line_number = line_number

    def get_children(self):
        return self.args

    def walk(self, walker):
        name = self.name.lower()
        method_name = "visit_distribution_" + name
        if hasattr(walker, method_name):
            return getattr(walker, method_name)(self)
        return super(AstDistribution, self).walk(walker)

    def __repr__(self):
        return "dist.{}({})".format(self.name, ', '.join([repr(arg) for arg in self.args]))


class AstExpr(Node):
    """
    `AstExpr` is a special node: it is not created by the parser but used inside the compiler to wrap already an
    compiled expression and its associated graph.
    """

    def __init__(self, graph: Graph, expr: str):
        self.graph = graph
        self.expr = expr

    @property
    def value(self):
        return self.graph, self.expr

    def __repr__(self):
        return "(GRAPH, {})".format(self.expr)


class AstFor(Node):

    def __init__(self, target, sequence, body: Node):
        self.target = target
        self.sequence = sequence
        self.body = body

    def __repr__(self):
        return "for({} in {}: {})".format(self.target, repr(self.sequence), repr(self.body))


class AstFunction(Node):

    def __init__(self, name, params, body: Node):
        self.name = name
        self.params = params
        self.body = body

    def __repr__(self):
        return "fn({} {} {})".format(self.name, repr(self.params), repr(self.body))


class AstFunctionCall(Node):

    def __init__(self, function, args):
        if isinstance(function, Symbol):
            function = function.name
        self.function = function
        self.args = args

    def get_children(self):
        return self.args

    def walk(self, walker):
        name = self.function
        if type(name) is str:
            method_name = "visit_call_" + name.replace('/', '_').replace('.', '_')
            if hasattr(walker, method_name):
                return getattr(walker, method_name)(self)

            if '/' in name:
                method_name = "visit_call_{}_functions".format(name[:name.index('/')])
                if hasattr(walker, method_name):
                    return getattr(walker, method_name)(self)

        return super(AstFunctionCall, self).walk(walker)

    def __repr__(self):
        return "{}({})".format(self.function, ', '.join([repr(arg) for arg in self.args]))


class AstIf(Node):

    def __init__(self, cond: AstCompare, if_body, else_body, line_number:int=-1):
        self.cond = cond
        self.if_body = if_body
        self.else_body = else_body
        self.line_number = line_number

    def get_children(self):
        if self.else_body:
            return [self.cond, self.if_body, self.else_body]
        else:
            return [self.cond, self.if_body]

    def __repr__(self):
        return "f({} {} {})".format(repr(self.cond), repr(self.if_body), repr(self.else_body))


class AstLet(Node):

    def __init__(self, bindings, body):
        self.bindings = bindings
        self.body = body

    def get_children(self):
        return [self.bindings, self.body]

    def __repr__(self):
        return "let({} {})".format(repr(self.bindings), repr(self.body))


class AstLoop(Node):

    def __init__(self, iter_count: int, arg: Node, function: Node, args: list):
        self.iter_count = iter_count
        self.arg = arg
        self.function = function
        if args:
            self.args = args
        else:
            self.args = []

    def __repr__(self):
        return "loop({}, {}, {})".format(self.iter_count, repr(self.arg), repr(self.function))


class AstMultiFor(Node):

    def __init__(self, targets, sources, body: Node):
        self.targets = targets
        self.sources = sources
        self.body = body

    def __repr__(self):
        return "multi-for({} in {}: {})".format(repr(self.targets), repr(self.sources), repr(self.body))


class AstObserve(Node):

    def __init__(self, distribution: AstDistribution, value, line_number:int=-1):
        self.distribution = distribution
        self.value = value
        self.line_number = line_number

    def __repr__(self):
        return "observe({}, {})".format(repr(self.distribution), repr(self.value))


class AstSample(Node):

    def __init__(self, distribution: AstDistribution, line_number:int=-1):
        self.distribution = distribution
        self.line_number = line_number

    def __repr__(self):
        return "sample({})".format(repr(self.distribution))


class AstSqrt(Node):

    def __init__(self, item: Node):
        self.item = item

    def __repr__(self):
        return "sqrt({})".format(repr(self.item))


class AstSymbol(Node):

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return "symbol({})".format(self.name)


class AstUnary(Node):

    def __init__(self, op: str, item: Node):
        if isinstance(op, Symbol):
            op = op.name
        self.op = op
        self.item = item

    def get_children(self):
        return [self.item]

    def __repr__(self):
        return self.op + repr(self.item)


class AstValue(Node):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return repr(self.value)


class AstVector(Node):

    def __init__(self, items):
        self.items = items

    def get_children(self):
        return self.items

    def __repr__(self):
        return '[{}]'.format(', '.join([repr(item) for item in self.items]))
