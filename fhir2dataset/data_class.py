"""classes representing the different types of information manipulated in FHIR2Dataset
"""
import re
import random
import logging
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
from pprint import pformat
from dataclasses import dataclass, field, asdict
from typing import Type, List, Optional

from fhir2dataset.visualization_tools import custom_repr
from fhir2dataset.fhirpath import parse_fhirpath


logger = logging.getLogger(__name__)


@dataclass
class SearchParameter:
    code: Optional[str] = field(default=None)
    fhirpath: Optional[str] = field(default=None)
    resource_types: Optional[List[str]] = field(default=None)
    prefix: Optional[str] = field(default=None)
    value: Optional[str] = field(default=None)


@dataclass
class Element:
    """unit entity that can be found in a fhir instance in json format using fhirpath or in a table in the col_name column.

    An element is destined to be associated with a single value. For example, if we want to retrieve the patient id of a bundle containing 2 patients, we will have to create 2 element instances.
    """  # noqa

    col_name: str
    fhirpath: str
    goal: str = field(default="select")  # select, where or join
    value: Optional[list] = field(default=None)
    concat_type: Optional[str] = field(default="cell")
    search_parameter: Optional[SearchParameter] = field(default=None)


@dataclass
class Elements:
    """collection allowing to group together elements"""

    elements: List[Element] = field(default_factory=list)

    def append(self, x):
        self.elements.append(x)

    def get_subset_elements(self, goal):
        return [element for element in self.elements if element.goal == goal]

    def compute_forest_fhirpaths(self):
        forest = Forest()
        for fhirpath in [element.fhirpath for element in self.elements]:
            forest.add_fhirpath(fhirpath)
        forest.simplify_trees()
        forest.parse_fhirpaths()
        self.forest = forest
        self.forest_dict = forest.create_forest_dict()


@dataclass
class ResourceAliasInfoBasic:
    alias: str
    resource_type: str
    elements: Elements() = field(default_factory=Elements())


class ResourceAliasInfo(ResourceAliasInfoBasic):
    def __repr__(self):
        return custom_repr(super().__repr__())


@dataclass
class EdgeInfo:
    parent: str
    child: str
    searchparam_parent: Optional[str] = field(default=None)
    join_how: str = field(default="inner")
    searchparam_prefix: Optional[dict] = field(default=None)


class SearchParameters:
    def __init__(self, search_parameters: List[Type[SearchParameter]] = None):
        if search_parameters:
            self.items = search_parameters
        else:
            self.items = []
        self._init_data()

    def add(self, search_parameters):
        if isinstance(search_parameters, SearchParameter):
            self.items.append(search_parameters)
            self._add_data(search_parameters)
        elif isinstance(search_parameters, list):
            self.items.extend(search_parameters)
            for search_parameter in search_parameters:
                self._add_data(search_parameter)
        else:
            raise TypeError(
                f"{search_parameters} should be a list or a SearchParameter type instead of "
                f"{type(search_parameters)} type"
            )

    def searchparam_to_fhirpath(self, search_param: str, resource_type: str = "all"):
        """Retrieve the fhirpath that allows to retrieve the element that is the object of
        a searchparam in a json instance (after the 'resource' key) of a resource of a certain
        type

        Arguments:
            resource_type {str} -- name of a resource type (e.g. 'Organization')
            search_param {str} -- name of a searchparam of this resource type (e.g. 'address-postalcode')

        Returns:
            str -- the fhirpath for retrieving the element that is the subject of the searchparam
            (e.g. 'address.postalCode')
        """  # noqa
        try:
            return self._data[search_param][resource_type]
        except KeyError:
            logger.warning(f"The searchparam '{search_param}' doesn't exist in the rules")
            return None

    def _init_data(self):
        self._data = defaultdict(lambda: defaultdict(dict))
        for search_parameter in self.items:
            self._add_data(search_parameter)

    def _add_data(self, search_parameter: Type[SearchParameter]):
        fhirpath = search_parameter.fhirpath
        data = self._data[search_parameter.code]
        for resource_type in search_parameter.resource_types:
            if resource_type not in data.keys():
                data[resource_type] = fhirpath
            else:
                raise ValueError(
                    f"the search parameter {search_parameter.code} is already recorded\n"
                    f"data already recorded: {pformat(self._data[search_parameter.code])}\n"
                    f"data given as argument: {search_parameter}\n"
                )


@dataclass(eq=True, frozen=True)
class Node:
    """Modeling a node of a process tree"""

    fhirpath: str
    index: str
    previous_node_hash: int = 0


def break_parenthesis(exp: str):
    sublist = re.split(r"(\(|\))", exp)
    return sublist


def split_fhirpath(fhirpath: str) -> List[Node]:
    """Transforms a fhirpath into a list of sub-fhirpaths that run one after the other would give
    the same result as the initial fhirpath.

    Args:
        fhirpath (str): a string of characters representing a fhirpath

    Returns:
        List[Node]: a list of Nodes representing the sub-fhirpaths described above

    Examples:
        1. "Patient.name.given" becomes ["Patient","name","given"]
        1. "Patient.name | Practitioner.name" becomes ["Patient.name | Practitioner.name"]
        2. "Patient.(x | y).use" becomes ["Patient","(x | y)","use"]
    """
    sub_paths = [sub_path for sub_path in fhirpath.split(".") if sub_path != ""]

    tmps_list = []
    tmp_word = ""
    num_brackets = 0
    num_or = fhirpath.count("|")

    for sub_path in sub_paths:
        tmp_word = f"{tmp_word}.{sub_path}" if tmp_word else sub_path
        for character in sub_path:
            if character == "(":
                num_brackets += 1
            elif character == ")":
                num_brackets -= 1
            elif character == "|" and num_brackets % 2 == 1:
                num_or -= 1
        if not num_brackets:
            tmps_list.append(tmp_word)
            tmp_word = ""
    if num_or != 0:
        tmps_list = [fhirpath]

    node_list = _create_node_list(tmps_list)
    logger.debug(f"the fhirpath: {fhirpath} is parsed in {[node.fhirpath for node in node_list]}")
    return node_list


def _create_node_list(sub_fhirpaths: List[str]):
    node_list = []
    node = None
    for idx, fhirpath in enumerate(sub_fhirpaths):
        if node:
            node = Node(fhirpath=fhirpath, index=str(idx), previous_node_hash=hash(node))
        else:
            node = Node(fhirpath=fhirpath, index=str(idx))
        node_list.append(node)
    return node_list


class Forest:
    """class modeling the entire set of process trees

    Attributes:
        trees (dict): dictionary where the key is the value of the root and the value of the
        associated complete tree
        num_exp (int): total number of fhirpath that will be computed by this process tree forest
    """

    def __init__(self):
        self.trees = {}
        self.num_exp = 0

    def add_fhirpath(self, fhirpath: str) -> None:
        """Adding a fhirpath to the forest is done in the following steps:
            1. the fhirpath is divided into sub-fhirpaths which executed one after the other give
            the same result as the execution of the whole fhirpath.
            2. these subfhirpaths are added to the forest, each subfhirpath representing a node of
            a tree. The interest is that if 2 fhirpaths share the same first sub-fhirpaths then they
            will share the same first nodes of the tree.

        Args:
            fhirpath (str): string representing a fhirpath
        """
        splitted_fhirpath = split_fhirpath(fhirpath)
        self.__add_splitted_fhirpath(splitted_fhirpath)

    def simplify_trees(self):
        """This function, executed once all the fhirpaths have been added, allows to reduce the
        trees in the forest. If a node has only one successor node and if they are tagged with
        exactly the same column numbers (the same processes), then they will be merged.
        """
        new_trees = {}
        for root, tree in self.trees.items():
            tree.simplify_tree()
            new_trees[tree.root] = tree
        self.trees = new_trees

    def parse_fhirpaths(self):
        """transforms each expression that corresponds to a sub fhirpath of a node into a parsed
        version used by the fhirpath.js library.
        """
        for tree in self.trees.values():
            tree.parse_fhirpaths()

    def create_forest_dict(self):
        """creates a dictionary modeling the forest understandable by the javascript function in
        the forest.js file

        Returns:
            dict: dictionary described above
        """
        forest_dict = {}
        for root, tree in self.trees.items():
            nodes = tree.graph.nodes
            edges = tree.graph.edges

            nodes_dict = {}
            for node in nodes:
                nodes_dict[str(hash(node))] = asdict(node)
                nodes_dict[str(hash(node))]["column_idx"] = nodes[node]["column_idx"]
                nodes_dict[str(hash(node))]["parsed_fhirpath"] = nodes[node]["parsed_fhirpath"]

            edges_array = []
            for edge in edges:
                edges_array.append([str(hash(edge[0])), str(hash(edge[1]))])

            forest_dict[str(hash(root))] = {"nodes_dict": nodes_dict, "edges_array": edges_array}
        return forest_dict

    def __add_splitted_fhirpath(self, splitted_fhirpath=List[Node]):
        root = splitted_fhirpath[0]
        if root not in self.trees.keys():
            self.trees[root] = Tree(root)
        self.trees[root].add_edges_from_splitted_fhirpath(splitted_fhirpath, self.num_exp)
        self.num_exp += 1


class Tree:
    """class modeling a process tree

    Attributes:
        root (Node): the root of the tree
        graph (nx.DiGraph): oriented graph representing the tree
    """

    def __init__(self, root: Node):
        self.root = root
        self.graph = nx.DiGraph()

    def add_edges_from_splitted_fhirpath(self, splitted_fhirpath: list, column_idx: int):
        """add splitted_fhirpath to the tree, each sub-part of the fhirpath representing a node of
        the tree. The interest is that if 2 fhirpaths share the same first sub-fhirpaths then they
        will share the same first nodes of the tree

        Args:
            splitted_fhirpath (List[str]): list of fhirpaths representing a process
            column_idx ([type]): column number corresponding to the process number
        """
        for node in splitted_fhirpath:
            if node in self.graph.nodes:
                self.graph.nodes[node]["column_idx"].append(column_idx)
            else:
                self.graph.add_node(node, column_idx=[column_idx])
        edges = []
        for idx in range(len(splitted_fhirpath) - 1):
            edges.append((splitted_fhirpath[idx], splitted_fhirpath[idx + 1]))
        self.graph.add_edges_from(edges)

    def parse_fhirpaths(self):
        """transforms each expression that corresponds to a sub fhirpath of a node into a parsed
        version used by the fhirpath.js library.
        """
        for node in nx.dfs_preorder_nodes(self.graph, self.root):
            self.graph.nodes[node]["parsed_fhirpath"] = parse_fhirpath(node.fhirpath)

    def simplify_tree(self):
        """This function, executed once all the fhirpaths have been added, allows to reduce the
        tree. If a node has only one successor node and if they are tagged with exactly the same
        column numbers (the same processes), then they will be merged.
        """
        tmp_root = self.root
        final_root = self.root
        new_graph = self.graph.copy()

        previous_node_new_graph = None
        previous_node_created_new_graph = None
        column_idx = nx.get_node_attributes(self.graph, "column_idx")

        for node_old_graph in nx.dfs_preorder_nodes(self.graph, self.root):
            successors_old_graph = list(self.graph.successors(node_old_graph))
            if len(successors_old_graph) == 1:
                successor_old_graph = successors_old_graph[0]
                if column_idx[successor_old_graph] == column_idx[node_old_graph]:
                    if (
                        previous_node_created_new_graph
                        and column_idx[successor_old_graph] == column_idx[node_old_graph]
                    ):
                        previous_node_new_graph = previous_node_created_new_graph
                    else:
                        previous_node_new_graph = node_old_graph

                    new_fhirpath = (
                        f"{previous_node_new_graph.fhirpath}.{successor_old_graph.fhirpath}"
                    )
                    new_index = f"{previous_node_new_graph.index}-{successor_old_graph.index}"
                    new_node_new_graph = Node(new_fhirpath, new_index)

                    nx.relabel_nodes(
                        new_graph, {successor_old_graph: new_node_new_graph}, copy=False
                    )
                    new_graph = nx.contracted_nodes(
                        new_graph, new_node_new_graph, previous_node_new_graph, self_loops=False
                    )
                    previous_node_created_new_graph = new_node_new_graph
                    if node_old_graph == tmp_root:
                        tmp_root = successor_old_graph
                        final_root = new_node_new_graph
            else:
                previous_node_created_new_graph = None
        self.graph = new_graph
        self.root = final_root


def hierarchy_pos(G, root=None, width=1.0, vert_gap=0.2, vert_loc=0, xcenter=0.5):  # noqa

    """
    From Joel's answer at https://stackoverflow.com/a/29597209/2966723.
    Licensed under Creative Commons Attribution-Share Alike

    If the graph is a tree this will return the positions to plot this in a
    hierarchical layout.

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
    plt.figure(figsize=(5, 5))
    layout = hierarchy_pos(graph)
    labels = nx.get_node_attributes(graph, "column_idx")
    for key, column_idx in labels.items():
        labels[key] = f"{key.fhirpath}\n{column_idx}"
    nx.draw_networkx(graph, labels=labels, pos=layout)
    plt.show()
