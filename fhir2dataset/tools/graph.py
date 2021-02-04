"""
    Module containing functions useful for the analysis and exploitation of graphs
"""

import networkx as nx
import logging


logger = logging.getLogger(__name__)


def join_path(graph: nx.Graph) -> list:
    """transforms the query graph into an Eulerian graph in order to be able to find an Eulerian path in it.

    An Eulerian path is a trail in a finite graph that visits every edge exactly once (allowing for revisiting vertices).
    Since the initial graph is not necessarily an Eulerian graph, the Eulerian path is reprocessed so that each join is made only once.

    Arguments:
        graph {nx.Graph} -- instance of GraphQuery

    Returns:
        list -- List of tuples indicating the successive joints to be made
    """  # noqa
    euler_graph = nx.eulerize(graph)
    euler_path = list(nx.eulerian_path(euler_graph))
    path = clean_euler_path(euler_path)
    return path


def clean_euler_path(eulerian_path: list) -> list:
    """Cleans a Eulerian path so that each edge (not directed) appears only once in the list. If a edge appears more than once, only the first occurrence is kept.

    Arguments:
        eulerian_path {list} -- Eulerian path

    Returns:
        list -- cleaned Eulerian path
    """  # noqa
    path = []
    for edge in eulerian_path:
        if edge not in path and edge[::-1] not in path:
            path.append(edge)
    return path
