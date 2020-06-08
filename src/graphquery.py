import json
import requests
import networkx as nx
import logging
from typing import Type

from src.fhirrules_getter import FHIRRules

logging.basicConfig(filename="data/log/logger.log", level=logging.DEBUG)


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

    def __init__(
        self,
        fhir_api_url: str,
        path: str = None,
        capabilitystatement_filename: str = "CapabilityStatement.json",
        searchparameters_filename: str = "SearchParameters.json",
    ) -> None:
        """Instantiate the class and create the query object

        Arguments:
            fhir_api_url {str} -- the Service Base URL (e.g. http://hapi.fhir.org/baseR4/)

        Keyword Arguments:
            path {str} -- path to the folder containing capabilitystatement_filename and searchparameters_filename files (default: {None})
            capabilitystatement_filename {str} -- filename of a json that contains a resource of type CapabilityStatement (default: {"CapabilityStatement.json"})
            searchparameters_filename {str} -- filename of a json that contains a resource of type SearchParameters  (default: {"SearchParameters.json"})
        """
        self.fhir_rules = FHIRRules(path=path)

        # to represent the relationships (references) between resources
        self.resources_alias_graph = nx.Graph()
        self.resources_alias_info = dict()

    def execute(
        self, select_dict: dict, from_dict: dict, join_dict: dict = None, where_dict: dict = None,
    ):
        """Populates the attributes resources_alias_graph and resources_alias_info according to the information filled in 

        Arguments:
            select_dict {dict} -- dictionary containing the elements to be selected from the different resources
            from_dict {dict} -- dictionary containing all requested resources

        Keyword Arguments:
            join_dict {dict} -- dictionary containing the inner join rules between resources (default: {None})
            where_dict {dict} -- dictionary containing the (cumulative) conditions to be met by the resources (default: {None})
        """
        self._from(**from_dict)
        if join_dict:
            self._join(**join_dict)
        if where_dict:
            self._where(**where_dict)
        self._select(**select_dict)

    def from_config(self, config: dict):
        """Populates the attributes resources_alias_graph and resources_alias_info according to the information given in the configuration file

        Arguments:
            config {dict} -- dictionary in the format of a configuration file
        """
        self.execute(
            from_dict=config.get("from", None),
            select_dict=config.get("select", None),
            where_dict=config.get("where", None),
            join_dict=config.get("join", None),
        )

    def _from(self, **resource_type_alias):
        """Initializes the graph nodes contained in resources_alias_graph and the dictionary of resources_alias_info information of the aliases listed in resource_type_alias

        Keyword Arguments:
            **resource_type_alias: the key corresponds to the alias and the value to the type of the resource.
        """
        for (ressource_alias, resource_type,) in resource_type_alias.items():
            dict_elements = {
                "select": [],
                "aditionnal_ressource": ["id"],
                # "aditionnal_root" : ["fullUrl"],
                "aditionnal_root": [],
                "where": [],
                "join": [],
            }
            dict_search_parameters = dict()

            self.resources_alias_graph.add_node(ressource_alias)

            self.resources_alias_info[ressource_alias] = {
                "resource_type": resource_type,
                "elements": dict_elements,
                "search_parameters": dict_search_parameters,
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
        for alias_parent, searchparam_dict in join_as.items():
            type_parent = self.resources_alias_info[alias_parent]["resource_type"]
            for (searchparam_parent, alias_child,) in searchparam_dict.items():

                # Update element to have in table
                element_join = self.fhir_rules.ressourcetype_searchparam_to_element(
                    resource_type=type_parent, search_param=searchparam_parent,
                )
                element_join = f"{element_join}.reference"
                self.resources_alias_info[alias_parent]["elements"]["join"].append(element_join)

                # Udpade Graph
                type_child = self.resources_alias_info[alias_child]["resource_type"]

                searchparam_parent_to_child = f"{searchparam_parent}:{type_child}."
                include = f"{type_parent}:{searchparam_parent}:" f"{type_child}"
                searchparam_child_to_parent = f"_has:{type_parent}:{searchparam_parent}:"
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
                )

                self.resources_alias_graph[alias_parent][alias_child].update(url_data)

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
        for ressource_alias, conditions in wheres.items():
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
                self.resources_alias_info[ressource_alias]["search_parameters"][search_param] = {
                    "prefix": prefix,
                    "value": value,
                }
                element = self.fhir_rules.ressourcetype_searchparam_to_element(
                    resource_type=self.resources_alias_info[ressource_alias]["resource_type"],
                    search_param=search_param,
                )
                self.resources_alias_info[ressource_alias]["elements"]["where"].append(element)

    def _select(self, **selects):
        """updates the resources_alias_info attribute with the elements that must be retrieved for each alias

        Keyword Arguments:
            **selects: the key is an alias, the value is a list containing expressions to leaf elements
        """
        for resource_alias in selects.keys():
            # handles the case of count
            if "count" == resource_alias:
                for ressource_alias_count in selects["count"]:
                    self.resources_alias_info[ressource_alias_count]["count"] = True
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
            self.resources_alias_graph, pos=layout, edge_labels=edge_labels, font_size=10,
        )
        plt.show()
