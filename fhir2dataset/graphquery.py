import json
import requests
import networkx as nx
import logging
from pprint import pformat
from typing import Type

from .fhirrules_getter import FHIRRules

logger = logging.getLogger(__name__)

MODIFIERS_POSS = [
    "missing",
    "exact",
    "contains",
    "text",
    "in",
    "below",
    "above",
    "not-in",
]


class GraphQuery:
    """Class for storing query information in the form of a graph.
    
    Attributes:
        resources_alias_graph {nx.Graph} -- The nodes correspond to the aliases involved in the query (filled in the "from") and stops the reference link between 2 aliases (filled in the "join").
        resources_alias_info {dict} -- Dictionary storing information about each alias: 
                                        * the type of the associated resource
                                        * the elements that must be retrieved from the json of a resource
                                        * a boolean indicating whether to return the number of instances of the resource that meets all these criteria or not
        fhir_rules {Type(FHIRRules)} -- an instance of an FHIRRules object which contains information specific to the FHIR standard and the API used (for example the expressions associated with the search param of a resource).
    """

    def __init__(self, fhir_api_url: str, fhir_rules: type(FHIRRules) = None) -> None:
        """Instantiate the class and create the query object

        Arguments:
            fhir_api_url {str} -- the Service Base URL (e.g. http://hapi.fhir.org/baseR4/)

        Keyword Arguments:
            fhir_rules {type(FHIRRules)} -- an instance of a FHIRRules-type object. If the instance is not filled a default version will be used. (default: {None})
        """
        self.fhir_api_url = fhir_api_url
        if not fhir_rules:
            fhir_rules = FHIRRules(fhir_api_url=self.fhir_api_url)
        self.fhir_rules = fhir_rules

        # to represent the relationships (references) between resources
        self.resources_alias_graph = nx.Graph()
        self.resources_alias_info = dict()

    def execute(
        self,
        select_dict: dict,
        from_dict: dict,
        join_dict: dict = None,
        where_dict: dict = None,
        default_element_concat_type: str = "cell",
    ):
        """Populates the attributes resources_alias_graph and resources_alias_info according to the information filled in 

        Arguments:
            select_dict {dict} -- dictionary containing the elements to be selected from the different resources
            from_dict {dict} -- dictionary containing all requested resources

        Keyword Arguments:
            join_dict {dict} -- dictionary containing the inner join rules between resources (default: {None})
            where_dict {dict} -- dictionary containing the (cumulative) conditions to be met by the resources (default: {None})
            default_element_concat_type {str} -- indicates how multiple occurrences of elements should be concatenated (cell: all in one cell, row: split in several rows, column: split in several columns) (default: {"cell"})
        """
        self._from(**from_dict)
        if join_dict:
            self._join(**join_dict)
        if where_dict:
            self._where(**where_dict)
        self._select(**select_dict)
        self._complete_element_concat_type_dict(default_element_concat_type)
        logger.info(f"The nodes are:{self.resources_alias_graph.nodes()}")
        logger.info(f"The edges are:")
        logger.info(pformat(list(self.resources_alias_graph.edges(data=True))))
        logger.info(f"The information gathered for each node is:")
        logger.info(pformat(self.resources_alias_info))

    def _complete_element_concat_type_dict(self, default_element_concat_type):
        for resource_alias in self.resources_alias_info.keys():
            elements = []
            for value in self.resources_alias_info[resource_alias]["elements"].values():
                elements.extend(value)
            for element in elements:
                if element not in list(
                    self.resources_alias_info[resource_alias][
                        "elements_concat_type"
                    ].keys()
                ):
                    self.resources_alias_info[resource_alias]["elements_concat_type"][
                        element
                    ] = default_element_concat_type

    def from_config(self, config: dict):
        """Populates the attributes resources_alias_graph and resources_alias_info according to the information given in the configuration file

        Arguments:
            config {dict} -- dictionary in the format of a configuration file
        """
        self.execute(
            from_dict=config.get("from"),
            select_dict=config.get("select"),
            where_dict=config.get("where"),
            join_dict=config.get("join"),
        )

    def _from(self, **resource_type_alias):
        """Initializes the graph nodes contained in resources_alias_graph and the dictionary of resources_alias_info information of the aliases listed in resource_type_alias

        Keyword Arguments:
            **resource_type_alias: the key corresponds to the alias and the value to the type of the resource.
        """
        for (resource_alias, resource_type,) in resource_type_alias.items():
            dict_elements = {
                "select": [],
                "additional_resource": ["id"],
                # "additional_root" : ["fullUrl"],
                "additional_root": [],
                "where": [],
                "join": [],
            }
            dict_elem_concat_type = {"id": "row"}
            dict_search_parameters = dict()

            self.resources_alias_graph.add_node(resource_alias)

            self.resources_alias_info[resource_alias] = {
                "resource_type": resource_type,
                "elements": dict_elements,
                "search_parameters": dict_search_parameters,
                "elements_concat_type": dict_elem_concat_type,
                "count": False,
            }

    def _join(self, **join_as):
        """Builds the reference links between the aliases involved in the query
        1. fills in the elements in attribute resources_alias_info to be retrieved from the json resource file to be able to make the joins
        2. creates the edges between the nodes of the relevant aliases in the resources_alias_graph attribute.

        Keyword Arguments:
            **join_as: the key is an alias of a parent resource and the value is a dictionary containing in the key the expression leading to the reference, and in the value the alias of the child resource.
        """
        # to do : change to check in searchParameters // review naming : element not very precise
        for join_how, relationships_dict in join_as.items():
            join_how = join_how.lower()
            assert join_how in [
                "inner",
                "child",
                "parent",
                "one",
            ], "Precise how to join"
            for (alias_parent, searchparam_dict,) in relationships_dict.items():
                type_parent = self.resources_alias_info[alias_parent]["resource_type"]
                for (searchparam_parent, alias_child,) in searchparam_dict.items():

                    # Update element to have in table
                    element_join = self.fhir_rules.resourcetype_searchparam_to_element(
                        resource_type=type_parent, search_param=searchparam_parent,
                    )
                    element_join = f"{element_join}.reference"
                    self.resources_alias_info[alias_parent]["elements"]["join"].append(
                        element_join
                    )
                    self.resources_alias_info[alias_parent]["elements_concat_type"][
                        element_join
                    ] = "row"
                    # Udpade Graph
                    type_child = self.resources_alias_info[alias_child]["resource_type"]

                    searchparam_parent_to_child = f"{searchparam_parent}:{type_child}."
                    include = f"{type_parent}:{searchparam_parent}:" f"{type_child}"
                    searchparam_child_to_parent = (
                        f"_has:{type_parent}:{searchparam_parent}:"
                    )
                    revinclude = f"{type_parent}:{searchparam_parent}:" f"{type_child}"
                    url_data = {
                        alias_parent: {
                            "searchparam_prefix": searchparam_parent_to_child,
                            "include_prefix": include,
                        },
                        alias_child: {
                            "searchparam_prefix": searchparam_child_to_parent,
                            "include_prefix": revinclude,
                        },
                    }

                    self.resources_alias_graph.add_edge(
                        alias_parent,
                        alias_child,
                        parent=alias_parent,
                        child=alias_child,
                        element_join=element_join,
                        join_how=join_how,
                    )

                    self.resources_alias_graph[alias_parent][alias_child].update(
                        url_data
                    )

                    # To do: make assert
                    # check = f"{type_parent}.{searchparam_parent}"
                    # if (
                    #     check
                    #     in self.fhir_rules.possible_references[type_parent][
                    #         "searchInclude"
                    #     ]
                    # )
                    # if (
                    #     check
                    #     in self.fhir_rules.possible_references[type_child][
                    #         "searchRevInclude"
                    #     ]
                    # ):
                    # else:
                    #     possibilities = self.fhir_rules.possible_references[
                    #         type_parent]["searchInclude"]
                    #     logging.info(f"{check} not in {possibilities}")

    def _where(self, **wheres):
        """updates the resources_alias_info attribute with the conditions that each alias must meet

        Keyword Arguments:
            **wheres: the key is an alias, the value is a dictionary containing itself keys which are searchparams and whose values must be respected by the associated search params.
        """
        for resource_alias, conditions in wheres.items():
            for search_param, value_full in conditions.items():
                # add assert search_param in CapabilityStatement

                # handles the case where a prefix has been specified
                # value_full={"ge": "1970"}
                if type(value_full) is dict:
                    for k, v in value_full.items():
                        prefix = k
                        value = v
                else:
                    prefix = None
                    value = value_full
                # to do verify we don't delete something
                # print(
                #     self.resources_alias_info[resource_alias][
                #         "search_parameters"
                #     ]
                # )
                self.resources_alias_info[resource_alias]["search_parameters"][
                    search_param
                ] = {
                    "prefix": prefix,
                    "value": value,
                }
                resource_type = self.resources_alias_info[resource_alias][
                    "resource_type"
                ]
                searchparam_to_element = self.fhir_rules.resourcetype_searchparam_to_element(
                    resource_type=resource_type, search_param=search_param,
                )
                if searchparam_to_element:
                    element = searchparam_to_element
                else:
                    element = search_param
                # print(f"element: {element}")
                modifier = element.split(":")[-1]
                if modifier in MODIFIERS_POSS:
                    element = ":".join(element.split(":")[:-1])
                    # print(f"element modified: {element}")
                self.resources_alias_info[resource_alias]["elements"]["where"].append(
                    element
                )

    def _select(self, **selects):
        """updates the resources_alias_info attribute with the elements that must be retrieved for each alias

        Keyword Arguments:
            **selects: the key is an alias, the value is a list containing expressions to leaf elements
        """
        for resource_alias in selects.keys():
            # handles the case of count
            if "count" == resource_alias:
                for resource_alias_count in selects["count"]:
                    self.resources_alias_info[resource_alias_count]["count"] = True
            self.resources_alias_info[resource_alias]["elements"]["select"] += selects[
                resource_alias
            ]

    def draw_relations(self):
        """draws the resources_alias_graph attribute
        """
        import matplotlib.pyplot as plt

        edge_labels = dict()
        for i in self.resources_alias_graph.edges(data=True):
            value = f""
            for key, infos in i[2].items():
                if isinstance(infos, dict):
                    for key_2, infos_2 in infos.items():
                        if value:
                            value = f"{value}\n{key}: {key_2}: {infos_2}"
                        else:
                            value = f"{key}: {key_2}: {infos_2}"
                else:
                    if value:
                        value = f"{value}\n{key}:{infos}"
                    else:
                        value = f"{key}:{infos}"
            edge_labels[i[0:2]] = value

        plt.figure(figsize=(15, 15))
        layout = nx.spring_layout(self.resources_alias_graph)
        nx.draw_networkx(self.resources_alias_graph, pos=layout)
        nx.draw_networkx_labels(self.resources_alias_graph, pos=layout)
        nx.draw_networkx_edge_labels(
            self.resources_alias_graph,
            pos=layout,
            edge_labels=edge_labels,
            font_size=10,
        )
        plt.show()
