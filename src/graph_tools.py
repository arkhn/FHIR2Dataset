"""
    Module containing functions useful for the analysis and exploitation of graphs
"""

import networkx as nx
import itertools
import types


def join_path(graph: nx.Graph) -> list:
    """transforms the query graph into an Eulerian graph in order to be able to find an Eulerian path in it.

    An Eulerian path is a trail in a finite graph that visits every edge exactly once (allowing for revisiting vertices).
    Since the initial graph is not necessarily an Eulerian graph, the Eulerian path is reprocessed so that each join is made only once.

    Arguments:
        graph {nx.Graph} -- instance of GraphQuery

    Returns:
        list -- List of tuples indicating the successive joints to be made
    """
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
    """
    path = []
    while eulerian_path:
        edge = eulerian_path.pop(0)
        path.append(edge)
        list_to_pop = []
        for ind in range(len(eulerian_path)):
            if edge[::-1] == eulerian_path[ind] or edge == eulerian_path[ind]:
                list_to_pop.append(ind)
        if list_to_pop:
            list_to_pop.sort(reverse=True)
            for ind in list_to_pop:
                eulerian_path.pop(ind)
    return path
