#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  14:22
Date created:  08/06/2018

License: MIT
'''
try:
    import networkx as _nx
except ModuleNotFoundError:
     _nx = None
try:
    import matplotlib.pyplot as _plt
    import matplotlib.patches as mpatches
except ModuleNotFoundError:
    _plt = None


def create_network_graph(vertices):
    """
    Create a `networkx` graph. Used by the method `display_graph()`.
    :return: Either a `networkx.DiGraph` instance or `None`.
    """
    if _nx:
        G = _nx.DiGraph()
        for v in vertices:
            G.add_node(v.display_name)
            for a in v.ancestors:
                G.add_edge(a.display_name, v.display_name)
        return G
    else:
        return None

def display_graph(vertices):
    """
    Transform the graph to a `networkx.DiGraph`-structure and display it using `matplotlib` -- if the necessary
    libraries are installed.
    :return: `True` if the graph was drawn, `False` otherwise.
    """
    G =create_network_graph(vertices)
    _is_conditioned = None
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
                                node_size=500,
                                nodelist=[v.display_name for v in vertices if v.is_sampled],
                                alpha=0.5)
        _nx.draw_networkx_nodes(G, pos,
                                node_color='b',
                                node_size=500,
                                nodelist=[v.display_name for v in vertices if v.is_observed],
                                alpha=0.5)

        for v in vertices:
            _nx.draw_networkx_edges(G, pos, arrows=True,arrowsize=22,
                                    edgelist=[(a.display_name, v.display_name) for a in v.ancestors])
            if v.condition_ancestors is not None and len(v.condition_ancestors) > 0:
                _is_conditioned = 1
                _nx.draw_networkx_edges(G, pos, arrows=True, arrowsize=22,
                                        style='dashed',
                                        edge_color='g',
                                        alpha=0.5,
                                        edgelist=[(a.display_name, v.display_name) for a in v.condition_ancestors])
        _nx.draw_networkx_labels(G, pos, font_size=8, font_color='k', font_weight='bold')

        # for node, _ in G.nodes():
        red_patch = mpatches.Circle((0,0), radius=2, color='r', label='Sampled Variables')
        blue_patch = mpatches.Circle((0,0), radius=2, color='b', label='Observed Variables')
        green_patch = mpatches.Circle((0,0), radius=2, color='g', label='Conditioned Variables') if _is_conditioned else 0
        if _is_conditioned:
            _plt.legend(handles=[red_patch, blue_patch, green_patch])
        else:
            _plt.legend(handles=[red_patch, blue_patch])
        _plt.show()


        return True
    else:
        return False