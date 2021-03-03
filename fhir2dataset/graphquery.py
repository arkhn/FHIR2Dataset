import logging
from collections import defaultdict
from pprint import pformat

import networkx as nx

from fhir2dataset.data_class import EdgeInfo, Element, Elements, ResourceAliasInfo, SearchParameter
from fhir2dataset.fhirrules import FHIRRules

logger = logging.getLogger(__name__)


class GraphQuery:
    """Class for storing query information in the form of a graph.

    Attributes:
        resources_graph (nx.Graph): The nodes correspond to the aliases involved in
            the query (filled in the "from") and stops the reference link between 2 aliases
            (filled in the "join").
        resources_by_alias (dict): Dictionary storing information about each alias:
            * the type of the associated resource
            * the elements that must be retrieved from the json of a resource
            * a boolean indicating whether to return the number of instances of the resource
              that meets all these criteria or not
        fhir_rules (FHIRRules): an instance of an FHIRRules object which contains information
            specific to the FHIR standard and the API used (for example the fhirpaths
            associated with the search param of a resource).
    """  # noqa

    def __init__(self, fhir_api_url: str, fhir_rules: FHIRRules) -> None:
        """Instantiate the class and create the query object

        Arguments:
            fhir_api_url (str): the Service Base URL (e.g. http://hapi.fhir.org/baseR4/)
            fhir_rules (FHIRRules): an instance of a FHIRRules-type object
        """  # noqa
        self.fhir_api_url = fhir_api_url
        self.fhir_rules = fhir_rules

        # to represent the relationships (references) between resources
        self.resources_graph = nx.Graph()
        self.resources_by_alias = defaultdict(ResourceAliasInfo)

    def build(
        self, select_dict: dict, from_dict: dict, join_dict: dict = None, where_dict: dict = None
    ):
        """Populates the attributes resources_graph and resources_by_alias according
        to the information filled in.

        Arguments:
            select_dict (dict): elements to be selected from the different resources
            from_dict (dict): all requested resources
            join_dict (dict): the inner join rules between resources (default: None)
            where_dict (dict): the (cumulative) conditions to be met by the resources (default: None)
        """  # noqa
        self._from(**from_dict)
        if join_dict:
            self._join(**join_dict)
        if where_dict:
            self._where(**where_dict)
        self._select(**select_dict)

        # FIXME: Need FHIR2Dataset#96
        # for resource_alias in self.resources_by_alias.keys():
        #     self.resources_by_alias[resource_alias].elements.compute_forest_fhirpaths()

        logger.info(f"The nodes are:{self.resources_graph.nodes()}")
        logger.info("The edges are:")
        logger.info(pformat(list(self.resources_graph.edges(data=True))))
        logger.info("The information gathered for each node is:")
        logger.info(pformat(self.resources_by_alias))

    def _from(self, **resource_type_alias):
        """Initializes the graph nodes contained in resources_graph and the dictionary
        of resources_by_alias information of the aliases listed in resource_type_alias

        Arguments:
            **resource_type_alias: the key corresponds to the alias and the value to the type of the resource.
        """  # noqa
        for resource_alias, resource_type in resource_type_alias.items():
            elements = Elements(
                [
                    Element(
                        col_name="from_id",
                        fhirpath="id",
                        concat_type="row",
                    )
                ]
            )

            self.resources_graph.add_node(resource_alias)

            self.resources_by_alias[resource_alias] = ResourceAliasInfo(
                alias=resource_alias, resource_type=resource_type, elements=elements
            )

    def _join(self, **join_as):
        """Builds the reference links between the aliases involved in the query
        * fills in the elements in attribute resources_by_alias to be retrieved from the
          json resource file to be able to make the joins
        * creates the edges between the nodes of the relevant aliases in the resources_graph
          attribute.

        Keyword Arguments:
            **join_as: the key is an alias of a parent resource and the value is a dictionary
                containing in the key the search parameter leading to the reference, and in the
                value the alias of the child resource.
        """  # noqa

        for join_how, relationships_dict in join_as.items():
            join_how = join_how.lower()
            if join_how not in ["inner", "child", "parent"]:
                raise ValueError("Invalid join: joins should be of type: inner, child or parent")

            for (alias_parent, searchparam_dict) in relationships_dict.items():
                type_parent = self.resources_by_alias[alias_parent].resource_type
                for (searchparam_parent, alias_child) in searchparam_dict.items():
                    # Update element to have in table
                    fhirpath = self.fhir_rules.searchparam_to_fhirpath(
                        resource_type=type_parent, search_param=searchparam_parent
                    )
                    if fhirpath is None:
                        raise ValueError(
                            f"The reference attribute in the JOIN clause should be a valid "
                            f"gaisearchparameter, but got '{searchparam_parent}'."
                        )

                    if " | " in fhirpath:
                        fhirpath_ref = f"(({fhirpath}).reference)"
                    else:
                        fhirpath_ref = f"({fhirpath}.reference)"

                    self.resources_by_alias[alias_parent].elements.append(
                        Element(
                            goal="join",
                            col_name=f"join_{searchparam_parent}",
                            fhirpath=fhirpath_ref,
                            concat_type="row",
                        )
                    )

                    # Update Graph
                    type_child = self.resources_by_alias[alias_child].resource_type

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

                    self.resources_graph.add_edge(alias_parent, alias_child, info=edge_info)

    def _where(self, **wheres):
        """updates the resources_by_alias attribute with the conditions that each alias must meet

        Keyword Arguments:
            **wheres: the key is an alias, the value is a dictionary containing itself keys which
                are searchparams and whose values must be respected by the associated search params
        """  # noqa
        for resource_alias, conditions in wheres.items():
            for search_param, values in conditions.items():
                fhirpath = self._check_searchparam_or_fhirpath(resource_alias, search_param)
                if not isinstance(values, list):
                    values = [values]

                for value in values:
                    prefix = None

                    # handle the case where a prefix has been specified
                    # value_full={"ge": "1970"}
                    if type(value) is dict:
                        for key, val in value.items():
                            prefix = key
                            value = val
                            break

                    search_param_obj = SearchParameter(
                        code=search_param, prefix=prefix, value=value
                    )
                    self.resources_by_alias[resource_alias].elements.append(
                        Element(
                            goal="where",
                            col_name=f"where_{search_param_obj.code}",
                            fhirpath=fhirpath,
                            search_parameter=search_param_obj,
                        )
                    )

    def _select(self, **selects):
        """updates the resources_by_alias attribute with the elements that must be retrieved
        for each alias

        Keyword Arguments:
            **selects: the key is an alias, the value is a list containing fhirpath to leaf
                elements
        """  # noqa
        for resource_alias, col_names in selects.items():
            for col_name in col_names:
                fhirpath = self._check_searchparam_or_fhirpath(resource_alias, col_name)
                self.resources_by_alias[resource_alias].elements.append(
                    Element(
                        goal="select",
                        col_name=col_name,
                        fhirpath=fhirpath,
                    )
                )

    def _check_searchparam_or_fhirpath(self, resource_alias: str, searchparam_or_fhirpath: str):
        """transforms searchparam_or_fhirpath into its fhirpath if it's a searchparam, otherwise it returns the argument as it was entered.

        Args:
            resource_alias (str): alias associated with a resource
            searchparam_or_fhirpath (str): string of characters that can correspond to a searchparam or a fhirpath

        Returns:
            str: string of characters corresponding to a fhirpath
        """  # noqa
        resource_type = self.resources_by_alias[resource_alias].resource_type
        fhirpath = self.fhir_rules.searchparam_to_fhirpath(
            resource_type=resource_type,
            search_param=searchparam_or_fhirpath,
        )
        return fhirpath or searchparam_or_fhirpath
