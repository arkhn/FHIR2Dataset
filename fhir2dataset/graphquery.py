import networkx as nx
import logging
from typing import Type
from pprint import pformat
from collections import defaultdict

from fhir2dataset.fhirrules_getter import FHIRRules
from fhir2dataset.visualization_tools import custom_repr

from fhir2dataset.data_class import SearchParameter, ResourceAliasInfo, Element, Elements, EdgeInfo

logger = logging.getLogger(__name__)


class GraphQuery:
    """Class for storing query information in the form of a graph.

    Attributes:
        resources_alias_graph {nx.Graph} -- The nodes correspond to the aliases involved in the query (filled in the "from") and stops the reference link between 2 aliases (filled in the "join").
        resources_alias_info {dict} -- Dictionary storing information about each alias:
                                        * the type of the associated resource
                                        * the elements that must be retrieved from the json of a resource
                                        * a boolean indicating whether to return the number of instances of the resource that meets all these criteria or not
        fhir_rules {Type(FHIRRules)} -- an instance of an FHIRRules object which contains information specific to the FHIR standard and the API used (for example the fhirpaths associated with the search param of a resource).
    """  # noqa

    def __init__(self, fhir_api_url: str, fhir_rules: type(FHIRRules) = None) -> None:
        """Instantiate the class and create the query object

        Arguments:
            fhir_api_url {str} -- the Service Base URL (e.g. http://hapi.fhir.org/baseR4/)

        Keyword Arguments:
            fhir_rules {type(FHIRRules)} -- an instance of a FHIRRules-type object. If the instance is not filled a default version will be used. (default: {None})
        """  # noqa
        self.fhir_api_url = fhir_api_url
        self.fhir_rules = fhir_rules or FHIRRules(fhir_api_url=self.fhir_api_url)

        # to represent the relationships (references) between resources
        self.resources_alias_graph = nx.Graph()
        self.resources_alias_info = defaultdict(Type[ResourceAliasInfo])

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
        """  # noqa
        self._from(**from_dict)
        if join_dict:
            self._join(**join_dict)
        if where_dict:
            self._where(**where_dict)
        self._select(**select_dict)

        for resource_alias in self.resources_alias_info.keys():
            self.resources_alias_info[resource_alias].elements.compute_forest_fhirpaths()

        logger.info(f"The nodes are:{self.resources_alias_graph.nodes()}")
        logger.info("The edges are:")
        logger.info(pformat(list(self.resources_alias_graph.edges(data=True))))
        logger.info("The information gathered for each node is:")
        logger.info(pformat(self.resources_alias_info))

    def from_config(self, config: dict):
        """Populates the attributes resources_alias_graph and resources_alias_info according to the information given in the configuration file

        Arguments:
            config {dict} -- dictionary in the format of a configuration file
        """  # noqa
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
        """  # noqa
        for (resource_alias, resource_type) in resource_type_alias.items():
            elements = Elements(
                [
                    Element(
                        goal="additional_resource",
                        col_name="from_id",
                        fhirpath="id",
                        concat_type="row",
                    )
                ]
            )

            self.resources_alias_graph.add_node(resource_alias)

            self.resources_alias_info[resource_alias] = ResourceAliasInfo(
                alias=resource_alias, resource_type=resource_type, elements=elements
            )

    def _join(self, **join_as):
        """Builds the reference links between the aliases involved in the query
        1. fills in the elements in attribute resources_alias_info to be retrieved from the json resource file to be able to make the joins
        2. creates the edges between the nodes of the relevant aliases in the resources_alias_graph attribute.

        Keyword Arguments:
            **join_as: the key is an alias of a parent resource and the value is a dictionary containing in the key the search parameter leading to the reference, and in the value the alias of the child resource.
        """  # noqa
        # TODO : review naming : element not very precise
        for join_how, relationships_dict in join_as.items():
            join_how = join_how.lower()
            assert join_how in ["inner", "child", "parent", "one"], "Precise how to join"
            for (alias_parent, searchparam_dict) in relationships_dict.items():
                type_parent = self.resources_alias_info[alias_parent].resource_type
                for (searchparam_parent, alias_child) in searchparam_dict.items():

                    # Update element to have in table
                    fhirpath_searchparam = self.fhir_rules.searchparam_to_fhirpath(
                        resource_type=type_parent, search_param=searchparam_parent
                    )
                    if " | " in fhirpath_searchparam:
                        fhirpath_ref = f"(({fhirpath_searchparam}).reference)"
                    else:
                        fhirpath_ref = f"({fhirpath_searchparam}.reference)"

                    self.resources_alias_info[alias_parent].elements.append(
                        Element(
                            goal="join",
                            col_name=f"join_{searchparam_parent}",
                            fhirpath=fhirpath_ref,
                            concat_type="row",
                        )
                    )

                    # Udpade Graph
                    type_child = self.resources_alias_info[alias_child].resource_type

                    searchparam_parent_to_child = f"{searchparam_parent}:{type_child}."
                    # include = f"{type_parent}:{searchparam_parent}:" f"{type_child}"

                    searchparam_child_to_parent = f"_has:{type_parent}:{searchparam_parent}:"
                    # revinclude = f"{type_parent}:{searchparam_parent}:" f"{type_child}"

                    searchparam_prefix = {
                        alias_parent: searchparam_parent_to_child,
                        alias_child: searchparam_child_to_parent,
                    }

                    edge_info = EdgeInfo(
                        parent=alias_parent,
                        child=alias_child,
                        searchparam_parent=searchparam_parent,
                        join_how=join_how,
                        searchparam_prefix=searchparam_prefix,
                    )

                    self.resources_alias_graph.add_edge(alias_parent, alias_child, info=edge_info)

    def _where(self, **wheres):
        """updates the resources_alias_info attribute with the conditions that each alias must meet

        Keyword Arguments:
            **wheres: the key is an alias, the value is a dictionary containing itself keys which are searchparams and whose values must be respected by the associated search params.
        """  # noqa
        for resource_alias, conditions in wheres.items():
            for search_param, value_full in conditions.items():

                # handles the case where a prefix has been specified
                # value_full={"ge": "1970"}
                if type(value_full) is dict:
                    for k, v in value_full.items():
                        prefix = k
                        value = v
                else:
                    prefix = None
                    value = value_full

                fhirpath = self._check_searchparam_or_fhirpath(resource_alias, search_param)

                search_param = SearchParameter(code=search_param, prefix=prefix, value=value)
                self.resources_alias_info[resource_alias].elements.append(
                    Element(
                        goal="where",
                        col_name=f"where_{search_param.code}",
                        fhirpath=fhirpath,
                        search_parameter=search_param,
                    )
                )

    def _select(self, **selects):
        """updates the resources_alias_info attribute with the elements that must be retrieved for each alias

        Keyword Arguments:
            **selects: the key is an alias, the value is a list containing fhirpath to leaf elements
        """  # noqa
        for resource_alias, col_names in selects.items():
            for col_name in col_names:
                fhirpath = self._check_searchparam_or_fhirpath(resource_alias, col_name)
                self.resources_alias_info[resource_alias].elements.append(
                    Element(goal="select", col_name=col_name, fhirpath=fhirpath)
                )

    def _check_searchparam_or_fhirpath(self, resource_alias: str, searchparam_or_fhirpath: str):
        """transforms searchparam_or_fhirpath into its fhirpath if it's a searchparam, otherwise it returns the argument as it was entered.

        Args:
            resource_alias (str): alias associated with a resource
            searchparam_or_fhirpath (str): string of characters that can correspond to a searchparam or a fhirpath

        Returns:
            str: string of characters corresponding to a fhirpath
        """  # noqa
        resource_type = self.resources_alias_info[resource_alias].resource_type
        searchparam_to_element = self.fhir_rules.searchparam_to_fhirpath(
            resource_type=resource_type,
            search_param=searchparam_or_fhirpath,
        )
        if searchparam_to_element:
            element = searchparam_to_element
        else:
            element = searchparam_or_fhirpath
        return element

    def draw_relations(self):
        """draws the resources_alias_graph attribute"""
        import matplotlib.pyplot as plt

        edge_labels = {}
        for i in self.resources_alias_graph.edges(data=True):
            edge_infos = custom_repr(i[2]["info"].__repr__())
            edge_labels[i[0:2]] = edge_infos

        plt.figure(figsize=(15, 15))
        layout = nx.spring_layout(self.resources_alias_graph)
        nx.draw_networkx(self.resources_alias_graph, pos=layout)
        nx.draw_networkx_labels(self.resources_alias_graph, pos=layout)
        nx.draw_networkx_edge_labels(
            self.resources_alias_graph,
            pos=layout,
            edge_labels=edge_labels,
            font_size=10,
            rotate=False,
            horizontalalignment="left",
        )
        plt.show()
