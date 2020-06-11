import json
import requests
import logging
import networkx as nx

from .graphquery import GraphQuery


logger = logging.getLogger(__name__)


class URLBuilder:
    """class that allows to build the url of a query that will be made for an alias of a FHIR resource to a FHIR api

    Attributes:
        fhir_api_url: The Service Base URL (e.g. http://hapi.fhir.org/baseR4/)
        main_resource_alias: alias given to a set of fhir resources of a certain type which are the subject of the api query
        search_query_url: url which will make it possible to recover the resources of the type of main_alias respecting as well as possible the conditions where on itself and on its neighbors.
    """

    def __init__(
        self, fhir_api_url: str, query_graph: type(GraphQuery), main_resource_alias: str
    ) -> None:
        """
        Arguments:
            fhir_api_url {str} -- The Service Base URL (e.g. http://hapi.fhir.org/baseR4/)
            query_graph {type(GraphQuery)} -- instance of a GraphQuery object that gives a graphical representation of the global query
            main_resource_alias {str} -- alias given to a set of fhir resources of a certain type
        """
        self.fhir_api_url = fhir_api_url
        self.main_resource_alias = main_resource_alias
        self._query_graph = query_graph

        self._url_params = None
        self._get_url_params()
        self.search_query_url = self._compute_url()

    def _compute_url(self) -> str:
        """Generates the url which will make it possible to recover the resources of the type of main_alias respecting as well as possible the conditions where on itself and on its neighbors.

        Returns:
            str -- corresponding API request url
        """
        # to do verify self.fhir_api_url finish by '/'
        search_query_url = (
            f"{self.fhir_api_url}{self._query_graph.resources_alias_info[self.main_resource_alias]['resource_type']}?"
            f"{self._url_params or ''}"
        )
        logger.info(f"the computed url is {search_query_url}")
        return search_query_url

    def _get_url_params(self):
        """retrieves the portions of the url that specify search parameters
        """
        for resource_alias in self._query_graph.resources_alias_info.keys():
            url_temp = None
            to_resource, reliable = self._light_chained_params(resource_alias)

            if reliable:
                infos_alias = self._query_graph.resources_alias_info[resource_alias]
                infos_search_param = infos_alias["search_parameters"]
                for search_param, values in infos_search_param.items():
                    # add assert search_param in CapabilityStatement
                    value = f"{values['prefix'] or ''}{values['value']}"
                    url_temp = f"{f'{url_temp}&' if url_temp else ''}{to_resource or ''}{search_param}={value}"

                self._url_params = f"{f'{self._url_params}&' if self._url_params else ''}{url_temp or ''}"
                logger.debug(
                    f"the part of the url for the params is: {self._url_params}"
                )

    # To change because it's useless to go through dijstra for the moment knowing that we only do chain parameters of length 1.
    def _light_chained_params(self, resource_alias: str) -> tuple:
        """gives the prefix (in the first element of the output tuple) to make a chained parameter from the main resource to the resource given as argument. If the resource given as argument is not a neighbor of the main resource, the second element of the output tuple is set to false

        Arguments:
            resource_alias {str} -- alias of a resource

        Returns:
            tuple -- (prefix, boolean)
        """
        to_resource = None
        reliable = True
        # Construction of the path from the main resource to the
        # resource on which the parameter(s) will be applied
        if resource_alias != self.main_resource_alias:
            reliable = False
        return to_resource, reliable

    def _chained_params(self, resource_alias: str) -> tuple:
        """gives the prefix (in the first element of the output tuple) to make a chained parameter from the main resource to the resource given as argument. If the resource given as argument is not a neighbor of the main resource, the second element of the output tuple is set to false

        Arguments:
            resource_alias {str} -- alias of a resource

        Returns:
            tuple -- (prefix, boolean)
        """
        to_resource = None
        reliable = True
        # Construction of the path from the main resource to the
        # resource on which the parameter(s) will be applied
        if resource_alias != self.main_resource_alias:
            internal_path = nx.shortest_path(
                self._query_graph.resources_alias_graph,
                source=self.main_resource_alias,
                target=resource_alias,
            )
            # because we are not sure about chaining
            if len(internal_path) <= 2:
                for ind in range(len(internal_path) - 1):
                    edge = self._query_graph.resources_alias_graph.edges[
                        internal_path[ind], internal_path[ind + 1]
                    ]
                    # logging.info(f"edge:{edge}")
                    searchparam_prefix = edge[internal_path[ind]]["searchparam_prefix"]
                    to_resource = f"{to_resource or ''}{searchparam_prefix}"
            else:
                reliable = False
        return to_resource, reliable
