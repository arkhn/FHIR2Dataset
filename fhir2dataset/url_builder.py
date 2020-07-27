import logging
import random
from typing import Type

from collections import defaultdict
from posixpath import join as urljoin
from urllib.parse import urlencode
from fhir2dataset.graphquery import GraphQuery
from fhir2dataset.data_class import SearchParameter


logger = logging.getLogger(__name__)


class URLBuilder:
    """class that allows to build the url of a query that will be made for an alias of a FHIR resource to a FHIR api

    Attributes:
        fhir_api_url: The Service Base URL (e.g. http://hapi.fhir.org/baseR4/)
        main_resource_alias: alias given to a set of fhir resources of a certain type which are the subject of the api query
        search_query_url: url which will make it possible to recover the resources of the type of main_alias respecting as well as possible the conditions where on itself and on its neighbors.
    """  # noqa

    def __init__(
        self, fhir_api_url: str, graph_query: type(GraphQuery), main_resource_alias: str
    ) -> None:
        """
        Arguments:
            fhir_api_url (str} -- The Service Base URL (e.g. http://hapi.fhir.org/baseR4/)
            graph_query {type(GraphQuery)} -- instance of a GraphQuery object that gives a graphical representation of the global query
            main_resource_alias {str} -- alias given to a set of fhir resources of a certain type
        """  # noqa
        self.fhir_api_url = fhir_api_url
        self.main_resource_alias = main_resource_alias
        self._graph_query = graph_query

        self._params = defaultdict(list)

    def compute(self):
        self._update_url_params()
        self.search_query_url = self._compute_url()
        return self.search_query_url

    def _compute_url(self) -> str:
        """Generates the url which will make it possible to recover the resources of the type of main_alias respecting as well as possible the conditions where on itself and on its neighbors.

        Returns:
            str -- corresponding API request url
        """  # noqa
        params = (
            f"{self._graph_query.resources_alias_info[self.main_resource_alias].resource_type}?"
            f"{urlencode(self._params , doseq=True)}"
        )
        search_query_url = urljoin(self.fhir_api_url, params)
        logger.info(f"the computed url is {search_query_url}")
        return search_query_url

    def _update_url_params(self):
        """retrieves the portions of the url that specify search parameters

        The FHIR API makes union when "where conditions" are requested for neighbouring resources 
        Only one "where condition" on every neighbouring resource is taken into account
        """  # noqa
        for resource_alias in self._graph_query.resources_alias_graph.neighbors(
            self.main_resource_alias
        ):
            edge_info = self._graph_query.resources_alias_graph.edges[
                self.main_resource_alias, resource_alias
            ]["info"]

            resource_alias_info = self._graph_query.resources_alias_info[resource_alias]
            elements = resource_alias_info.elements.get_subset_elements(goal="where")

            # check if there are "where conditions" on resource_alias
            if elements:
                # select a random "where condition" on resource_alias
                element = random.choice(list(elements))
                search_param = element.search_parameter
                searchparam_prefixe = edge_info.searchparam_prefix[self.main_resource_alias]

                self._update_params_dict(search_param, searchparam_prefixe=searchparam_prefixe)

                logger.debug(f"the part of the url for the params is: {self._params}")

        # "where condition" on the resource itself
        resource_alias_info = self._graph_query.resources_alias_info[self.main_resource_alias]
        elements = resource_alias_info.elements.get_subset_elements(goal="where")

        for element in elements:
            self._update_params_dict(element.search_parameter)

        logger.debug(f"the part of the url for the params is: {self._params}")

    def _update_params_dict(
        self, search_param: Type[SearchParameter], searchparam_prefixe: str = ""
    ):
        key = f"{searchparam_prefixe}{search_param.code}"
        value = f"{search_param.prefix or ''}{search_param.value}"
        self._params[key] = value
