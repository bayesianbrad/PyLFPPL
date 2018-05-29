#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Dec 2017, Tobias Kohn
# 11. May 2018, Tobias Kohn
#
# We try to import `networkx` and `matplotlib`. If present, these packages can be used to get a visual
# representation of the graph. But neither of these packages is actually needed.
try:
    import networkx as _nx
except ModuleNotFoundError:
    _nx = None
try:
    import matplotlib.pyplot as _plt
except ModuleNotFoundError:
    _plt = None


class GraphPlotter(object):

    def create_network_graph(self):
        """
        Create a `networkx` graph. Used by the method `display_graph()`.

        :return: Either a `networkx.DiGraph` instance or `None`.
        """
        if _nx:
            G = _nx.DiGraph()
            for v in self.vertices:
                G.add_node(v.display_name)
                for a in v.ancestors:
                    G.add_edge(a.display_name, v.display_name)
            return G
        else:
            return None

    def display_graph(self):
        """
        Transform the graph to a `networkx.DiGraph`-structure and display it using `matplotlib` -- if the necessary
        libraries are installed.

        :return: `True` if the graph was drawn, `False` otherwise.
        """
        G = self.create_network_graph()
        if _nx and _plt and G:
            try:
                from networkx.drawing.nx_agraph import graphviz_layout
                pos = graphviz_layout(G, prog='dot')
            except ModuleNotFoundError:
                from networkx.drawing.layout import shell_layout
                pos = shell_layout(G)
            except ImportError:
                from networkx.drawing.layout import shell_layout
                pos = shell_layout(G)
            _plt.subplot(111)
            _plt.axis('off')
            _nx.draw_networkx_nodes(G, pos,
                                    node_color='r',
                                    node_size=1250,
                                    nodelist=[v.display_name for v in self.vertices if v.is_sampled])
            _nx.draw_networkx_nodes(G, pos,
                                    node_color='b',
                                    node_size=1250,
                                    nodelist=[v.display_name for v in self.vertices if v.is_observed])
            for v in self.vertices:
                _nx.draw_networkx_edges(G, pos, arrows=True,
                                        edgelist=[(a.display_name, v.display_name) for a in v.ancestors])
                if v.condition_ancestors is not None and len(v.condition_ancestors) > 0:
                    _nx.draw_networkx_edges(G, pos, arrows=True,
                                            style='dashed',
                                            edge_color='g',
                                            edgelist=[(a.display_name, v.display_name) for a in v.condition_ancestors])
            _nx.draw_networkx_labels(G, pos, font_color='w', font_weight='bold')
            _plt.show()
            return True
        else:
            return False
