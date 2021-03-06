import logging
from collections import defaultdict
from posixpath import join as urljoin
from typing import Type

from fhir2dataset.data_class import SearchParameter
from fhir2dataset.graphquery import GraphQuery

logger = logging.getLogger(__name__)


class URLBuilder:
    """class that allows to build the url of a query that will be made for an alias
    of a FHIR resource to a FHIR api

    Attributes:
        fhir_api_url (str): The Service Base URL (e.g. http://hapi.fhir.org/baseR4/)
        graph_query (GraphQuery): instance of a GraphQuery object that gives a graphical
            representation of the global query
        main_resource_alias (str): alias given to a set of fhir resources of a certain type
            which are the subject of the api query
    """  # noqa

    def __init__(
        self, fhir_api_url: str, graph_query: GraphQuery, main_resource_alias: str
    ) -> None:
        """
        Arguments:
            fhir_api_url (str): The Service Base URL (e.g. http://hapi.fhir.org/baseR4/)
            graph_query (GraphQuery): instance of a GraphQuery object that gives a graphical
                representation of the global query
            main_resource_alias (str): alias given to a set of fhir resources of a certain type
        """  # noqa
        self.fhir_api_url = fhir_api_url
        self.graph_query = graph_query
        self.main_resource_alias = main_resource_alias

        self._params = defaultdict(list)

    def compute(self):
        self._update_url_params()
        return self._compute_url()

    def _compute_url(self) -> str:
        """Generates the url which will make it possible to recover the resources of the type
        of main_alias respecting as well as possible the conditions where on itself and on its
        neighbors.

        Returns:
            str: corresponding API request url
        """  # noqa
        params = f"{self.graph_query.resources_by_alias[self.main_resource_alias].resource_type}?"

        for key, values in self._params.items():
            for value in values:
                params += f"{key}={value}&"

        # Rm last '&'
        params = params[:-1]

        search_query_url = urljoin(self.fhir_api_url, params)
        logger.info(f"the computed url is {search_query_url}")
        return search_query_url

    def _update_url_params(self):
        """retrieves the portions of the url that specify search parameters

        The FHIR API makes union when "where conditions" are requested for neighbouring resources
        Only one "where condition" on every neighbouring resource is taken into account
        """  # noqa
        for resource_alias in self.graph_query.resources_graph.neighbors(self.main_resource_alias):
            edge_info = self.graph_query.resources_graph.edges[
                self.main_resource_alias, resource_alias
            ]["info"]
            if edge_info.join_how == "child":
                continue

            resource = self.graph_query.resources_by_alias[resource_alias]
            elements = resource.elements.where(goal="where")

            # Update url for each condition in "where conditions" on resource_alias
            for element in elements:
                search_param = element.search_parameter
                searchparam_prefix = edge_info.searchparam_prefix[self.main_resource_alias]

                self._update_params_dict(search_param, searchparam_prefix=searchparam_prefix)

            logger.debug(f"the part of the url for the params is: {self._params}")

        # "where condition" on the resource itself
        resource_alias_info = self.graph_query.resources_by_alias[self.main_resource_alias]
        elements = resource_alias_info.elements.where(goal="where")

        for element in elements:
            self._update_params_dict(element.search_parameter)

        logger.debug(f"the part of the url for the params is: {self._params}")

    def _update_params_dict(
        self, search_param: Type[SearchParameter], searchparam_prefix: str = ""
    ):
        key = f"{searchparam_prefix}{search_param.code}"
        value = f"{search_param.prefix or ''}{search_param.value}"

        self._params[key].append(value)
