import json
import requests
import networkx as nx

from src.graphquery import GraphQuery


class URLBuilder:
    """class that allows to build the url of a query that will be made for an alias of a FHIR resource to a FHIR api
    """
    def __init__(
        self,
        fhir_api_url: str,
        query_graph: type(GraphQuery),
        main_resource_alias: str
    ) -> None:
        self.fhir_api_url = fhir_api_url
        self.query_graph = query_graph
        self.main_resource_alias = main_resource_alias

        self._url_params = None
        self._get_url_params()
        self.search_query_url = self._compute_url()

    def _compute_url(self) -> str:
        """Generates the API request url satisfying the conditions from,
        join, where and select

        Returns:
            str -- corresponding API request url
        """
        # to do verify self.fhir_api_url finish by '/'
        search_query_url = (
            f"{self.fhir_api_url}{self.query_graph.resources_alias_info[self.main_resource_alias]['resource_type']}?"
            f"{self._url_params or ''}&_format=json"
        )
        return search_query_url

    def _get_url_params(self):
        for ressource_alias in self.query_graph.resources_alias_info.keys():
            url_temp = None
            to_resource, reliable = self._chained_params(ressource_alias)

            if reliable:
                for search_param, values in self.query_graph.resources_alias_info[ressource_alias][
                    "search_parameters"].items():
                    # add assert search_param in CapabilityStatement
                    value = f"{values['prefix'] or ''}{values['value']}"
                    url_temp = (
                            f"{f'{url_temp}&' if url_temp else ''}{to_resource or ''}{search_param}={value}"
                        )

                self._url_params = (
                        f"{f'{self._url_params}&' if self._url_params else ''}{url_temp or ''}"
                        )
                # logging.info(f"url_params: {self._url_params}")

    def _chained_params(self, ressource_alias):
        to_resource = None
        reliable = True
        # Construction of the path from the main resource to the
        # resource on which the parameter(s) will be applied
        if ressource_alias != self.main_resource_alias:
            internal_path = nx.shortest_path(
                self.query_graph.resources_alias_graph,
                source=self.main_resource_alias,
                target=ressource_alias,
            )
            # because we are not sure about chaining
            if len(internal_path) <= 2:
                for ind in range(len(internal_path) - 1):
                    edge = self.query_graph.resources_alias_graph.edges[
                        internal_path[ind], internal_path[ind + 1]
                    ]
                    #logging.info(f"edge:{edge}")
                    searchparam_prefix = edge[internal_path[ind]]["searchparam_prefix"]
                    to_resource = (
                            f"{to_resource or ''}{searchparam_prefix}"
                        )
            else:
                reliable = False
        return to_resource, reliable