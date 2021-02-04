import random

import matplotlib.pyplot as plt
import networkx as nx

OPEN_CHAR = ["[", "{", "("]
CLOSE_CHAR = ["]", "}", ")"]
SAFE_CHAR = ["'", '"']
DEFAULT_BREAKLINE_CHAR = "\n"
DEFAULT_INDENT_CHAR = " "


def draw_graphquery(resources_alias_graph):
    """draws the resources_graph attribute"""
    import matplotlib.pyplot as plt

    edge_labels = {}
    for i in resources_alias_graph.edges(data=True):
        edge_infos = custom_repr(i[2]["info"].__repr__())
        edge_labels[i[0:2]] = edge_infos

    plt.figure(figsize=(15, 15))
    layout = nx.spring_layout(resources_alias_graph)
    nx.draw_networkx(resources_alias_graph, pos=layout)
    nx.draw_networkx_labels(resources_alias_graph, pos=layout)
    nx.draw_networkx_edge_labels(
        resources_alias_graph,
        pos=layout,
        edge_labels=edge_labels,
        font_size=10,
        rotate=False,
        horizontalalignment="left",
    )
    plt.show()


def custom_repr(
    string: str,
    indent_width: int = 4,
    breakline_char: str = DEFAULT_BREAKLINE_CHAR,
    indent_char: str = DEFAULT_INDENT_CHAR,
):
    nested_int = 0
    new_string = ""
    safe_zone = False
    len_breakline_char = len(breakline_char)
    for character in string:
        if character in SAFE_CHAR:
            safe_zone = not safe_zone
            new_string += character
        elif safe_zone:
            new_string += character
        elif character in OPEN_CHAR:
            nested_int += 1
            new_string += character + breakline_char + nested_int * indent_width * indent_char
        elif character == ",":
            if new_string[-len_breakline_char:] == breakline_char:
                new_string = new_string[:-len_breakline_char]
            new_string += "," + breakline_char + (nested_int * (indent_width) - 1) * indent_char
        elif character in CLOSE_CHAR:
            nested_int -= 1
            if new_string[-len_breakline_char:] == breakline_char:
                new_string = new_string[:-len_breakline_char]
            new_string += (
                breakline_char
                + nested_int * indent_width * indent_char
                + character
                + breakline_char
            )
        else:
            new_string += character
    return new_string


def hierarchy_pos(G, root=None, width=1.0, vert_gap=0.2, vert_loc=0, xcenter=0.5):  # noqa
    """
    From Joel's answer at https://stackoverflow.com/a/29597209/2966723.
    Licensed under Creative Commons Attribution-Share Alike

    If the graph is a tree this will return the positions to plot this in a
    hierarchical layout.

    Arguments:
        G: the graph (must be a tree)
        root: the root node of current branch
            - if the tree is directed and this is not given,
              the root will be found and used
            - if the tree is directed and this is given, then
              the positions will be just for the descendants of this node.
            - if the tree is undirected and not given,
              then a random choice will be used.
        width: horizontal space allocated for this branch - avoids overlap with other branches
        vert_gap: gap between levels of hierarchy
        vert_loc: vertical location of root
        xcenter: horizontal location of root
    """
    if not nx.is_tree(G):
        raise TypeError("cannot use hierarchy_pos on a graph that is not a tree")

    if root is None:
        if isinstance(G, nx.DiGraph):
            root = next(
                iter(nx.topological_sort(G))
            )  # allows back compatibility with nx version 1.11
        else:
            root = random.choice(list(G.nodes))

    def _hierarchy_pos(
        G, root, width=1.0, vert_gap=0.2, vert_loc=0, xcenter=0.5, pos=None, parent=None  # noqa
    ):
        """
        see hierarchy_pos docstring for most arguments

        pos: a dict saying where all nodes go if they have been assigned
        parent: parent of this branch. - only affects it if non-directed

        """

        if pos is None:
            pos = {root: (xcenter, vert_loc)}
        else:
            pos[root] = (xcenter, vert_loc)
        children = list(G.neighbors(root))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)
        if len(children) != 0:
            dx = width / len(children)
            nextx = xcenter - width / 2 - dx / 2
            for child in children:
                nextx += dx
                pos = _hierarchy_pos(
                    G,
                    child,
                    width=dx,
                    vert_gap=vert_gap,
                    vert_loc=vert_loc - vert_gap,
                    xcenter=nextx,
                    pos=pos,
                    parent=root,
                )
        return pos

    return _hierarchy_pos(G, root, width, vert_gap, vert_loc, xcenter)


def show_tree(graph, number=None):
    """
    Function used to plot the graph query
    """
    plt.figure(figsize=(5, 5))
    layout = hierarchy_pos(graph)
    labels = nx.get_node_attributes(graph, "column_idx")
    for key, column_idx in labels.items():
        labels[key] = f"{key.fhirpath}\n{column_idx}"
    nx.draw_networkx(graph, labels=labels, pos=layout)
    plt.show()
