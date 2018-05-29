#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 12. Mar 2018, Tobias Kohn
# 19. Mar 2018, Tobias Kohn
#
import datetime
from pyppl.graphs import *
from pyppl.ppl_ast import *


class GraphCodeGenerator(object):

    def __init__(self, nodes: list, state_object: Optional[str]=None, imports: Optional[str]=None):
        self.nodes = nodes
        self.state_object = state_object
        self.imports = imports

    def generate_model_code(self, *,
                            class_name: str='Model',
                            base_class: str='',
                            imports: str='') -> str:

        if self.imports is not None:
            imports = self.imports + "\n" + imports
        if base_class is None:
            base_class = ''
        result = ["# {}".format(datetime.datetime.now()),
                  imports,
                  "class {}({}):".format(class_name, base_class)]

        doc_str = self.generate_doc_string()
        if doc_str is not None:
            result.append('\t"""\n\t{}\n\t"""'.format(doc_str.replace('\n', '\n\t')))
        result.append('')

        init_method = self.generate_init_method()
        if init_method is not None:
            result.append('\t' + init_method.replace('\n', '\n\t'))

        repr_method = self.generate_repr_method()
        if repr_method is not None:
            result.append('\t' + repr_method.replace('\n', '\n\t'))

        methods = [x for x in dir(self) if x.startswith('gen_') or x.startswith('get_')]
        for method in methods:
            code = getattr(self, method)()
            if type(code) is tuple and len(code) == 2:
                args, code = code
                args = 'self, ' + args
            else:
                args = 'self'
            code = code.replace('\n', '\n\t\t')
            result.append("\tdef {}({}):\n\t\t{}\n".format(method, args, code))

        return '\n'.join(result)

    def generate_doc_string(self):
        return None

    def generate_init_method(self):
        return "def __init__(self, vertices: set, arcs: set, data: set, conditionals: set):\n" \
               "\tsuper().__init__()\n" \
               "\tself.vertices = vertices\n" \
               "\tself.arcs = arcs\n" \
               "\tself.data = data\n" \
               "\tself.conditionals = conditionals\n"

    def generate_repr_method(self):
        s = "def __repr__(self):\n" \
            "\tV = '\\n'.join(sorted([repr(v) for v in self.vertices]))\n" \
            "\tA = ', '.join(['({}, {})'.format(u.name, v.name) for (u, v) in self.arcs]) if len(self.arcs) > 0 else '  -'\n" \
            "\tC = '\\n'.join(sorted([repr(v) for v in self.conditionals])) if len(self.conditionals) > 0 else '  -'\n" \
            "\tD = '\\n'.join([repr(u) for u in self.data]) if len(self.data) > 0 else '  -'\n" \
            "\tgraph = 'Vertices V:\\n{V}\\nArcs A:\\n  {A}\\n\\nConditions C:\\n{C}\\n\\nData D:\\n{D}\\n'.format(V=V, A=A, C=C, D=D)\n" \
            "\treturn graph\n"
        return s

    def get_vertices(self):
        return "return self.vertices"

    def get_vertices_names(self):
        return "return [v.name for v in self.vertices]"

    def get_arcs(self):
        return "return self.arcs"

    def get_arcs_names(self):
        return "return [(u.name, v.name) for (u, v) in self.arcs]"

    def get_conditions(self):
        return "return self.conditionals"

    def gen_cond_vars(self):
        return "return [c.name for c in self.conditionals]"

    def gen_if_vars(self):
        return "return [v.name for v in self.vertices if v.is_conditional and v.is_sampled and v.is_continuous]"

    def gen_cont_vars(self):
        return "return [v.name for v in self.vertices if v.is_continuous and not v.is_conditional and v.is_sampled]"

    def gen_disc_vars(self):
        return "return [v.name for v in self.vertices if v.is_discrete and v.is_sampled]"

    def get_vars(self):
        return "return [v.name for v in self.vertices if v.is_sampled]"

    def gen_log_pdf(self):
        distribution = None
        logpdf_code = ["log_pdf = 0"]
        state = self.state_object
        for node in self.nodes:
            name = node.name
            if state is not None:
                name = "{}['{}']".format(state, name)

            if isinstance(node, Vertex):
                code = "dst_ = {}".format(node.get_code())
                if code != distribution:
                    logpdf_code.append(code)
                    distribution = code
                logpdf_code.append("log_pdf += dst_.log_pdf({})".format(name))

            elif not isinstance(node, DataNode):
                code = "{} = {}".format(name, node.get_code())
                logpdf_code.append(code)

        logpdf_code.append("return log_pdf")
        return 'state', '\n'.join(logpdf_code)

    def gen_log_pdf_transformed(self):
        distribution = None
        logpdf_code = ["log_pdf = 0"]
        state = self.state_object
        for node in self.nodes:
            name = node.name
            if state is not None:
                name = "{}['{}']".format(state, name)

            if isinstance(node, Vertex):
                code = "dst_ = {}".format(node.get_code(transformed=True))
                if code != distribution:
                    logpdf_code.append(code)
                    distribution = code
                logpdf_code.append("log_pdf += dst_.log_pdf({})".format(name))

            elif not isinstance(node, DataNode):
                code = "{} = {}".format(name, node.get_code())
                logpdf_code.append(code)

        logpdf_code.append("return log_pdf")
        return 'state', '\n'.join(logpdf_code)

    def gen_prior_samples(self):
        distribution = None
        state = self.state_object
        if state is not None:
            sample_code = [state + " = {}"]
        for node in self.nodes:
            name = node.name
            if state is not None:
                name = "{}['{}']".format(state, name)

            if isinstance(node, Vertex):
                if node.has_observation:
                    sample_code.append("{} = {}".format(name, node.observation))
                else:
                    code = "dst_ = {}".format(node.get_code())
                    if code != distribution:
                        sample_code.append(code)
                        distribution = code
                    if node.sample_size > 1:
                        sample_code.append("{} = dst_.sample(sample_size={})".format(name, node.sample_size))
                    else:
                        sample_code.append("{} = dst_.sample()".format(name))

            else:
                code = "{} = {}".format(name, node.get_code())
                sample_code.append(code)

        if state is not None:
            sample_code.append("return " + state)
        return '\n'.join(sample_code)

    def gen_prior_samples_transformed(self):
        distribution = None
        state = self.state_object
        if state is not None:
            sample_code = [state + " = {}"]
        for node in self.nodes:
            name = node.name
            if state is not None:
                name = "{}['{}']".format(state, name)

            if isinstance(node, Vertex):
                if node.has_observation:
                    sample_code.append("{} = {}".format(name, node.observation))
                else:
                    code = "dst_ = {}".format(node.get_code(transformed=True))
                    if code != distribution:
                        sample_code.append(code)
                        distribution = code
                    if node.sample_size > 1:
                        sample_code.append("{} = dst_.sample(sample_size={})".format(name, node.sample_size))
                    else:
                        sample_code.append("{} = dst_.sample()".format(name))

            else:
                code = "{} = {}".format(name, node.get_code())
                sample_code.append(code)

        if state is not None:
            sample_code.append("return " + state)
        return '\n'.join(sample_code)
