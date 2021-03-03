import json
import logging
import os
from collections import defaultdict
from functools import lru_cache
from typing import List

from fhir2dataset.data_class import SearchParameter

logger = logging.getLogger(__name__)

DEFAULT_METADATA_DIR = "tools/metadata"


class SearchParameters:
    def __init__(self, search_parameters: List[SearchParameter] = None):
        self.items = search_parameters or []
        self._data = defaultdict(lambda: defaultdict(dict))

        for search_parameter in self.items:
            self._add_data(search_parameter)

    def add(self, search_parameters):
        if isinstance(search_parameters, SearchParameter):
            self.items.append(search_parameters)
            self._add_data(search_parameters)
        elif isinstance(search_parameters, list):
            for search_parameter in search_parameters:
                self.add(search_parameter)
        else:
            raise TypeError(
                f"{search_parameters} should be a list or a SearchParameter type instead of "
                f"{type(search_parameters)} type"
            )

    def searchparam_to_fhirpath(self, search_param: str, resource_type: str = "all"):
        """Retrieve the fhirpath associated to a searchparam of a certain resource type

        Arguments:
            resource_type (str): name of a resource type (e.g. 'Organization')
            search_param (str): searchparam of this resource type (e.g. 'address-postalcode')

        Returns:
            str: the fhirpath associated to the searchparam (e.g. 'address.postalCode')
        """  # noqa
        fhirpath = self._data[search_param][resource_type]

        if fhirpath == {}:  # self._data is a defaultdict of dict: so it never KeyErrors
            logger.info(f"The searchparam '{search_param}' doesn't exist in the rules")
            return None

        return fhirpath

    def _add_data(self, search_parameter: SearchParameter):
        """Fill the _data store dict with information from a searchparam"""
        fhirpath = search_parameter.fhirpath
        code = search_parameter.code
        resource_types = search_parameter.resource_types

        for resource_type in resource_types:
            self._data[code][resource_type] = fhirpath


class FHIRRules:
    """Class storing rules specific to the FHIR syntax and/or the FHIR API used,
    such as the search parameters

    Attributes:
        searchparameters (SearchParameters): an instance json of a SearchParameters resource
    """  # noqa

    def __init__(
        self,
        fhir_api_url: str = None,
        path: str = None,
        searchparameters_filename: str = "SearchParameters.json",
    ):
        """
        Arguments:
            fhir_api_url (str): The Service Base URL (e.g. http://hapi.fhir.org/baseR4/)
                (default: {None})
            path (str): path to the folder containing the searchparameters file (default: None)
            searchparameters_filename (str): filename of a json that contains a resource of
                type SearchParameters  (default: {"SearchParameters.json"})
        """  # noqa
        self.fhir_api_url = fhir_api_url
        self.path = path or os.path.join(os.path.dirname(__file__), DEFAULT_METADATA_DIR)
        self.searchparameters_filename = searchparameters_filename
        self.searchparameters = self.build_searchparameters()

    @lru_cache(maxsize=10000)
    def searchparam_to_fhirpath(self, search_param: str, resource_type: str = "all"):
        """Retrieve the fhirpath associated to a searchparam of a certain resource type,
        and filter it to only clauses that are associated to the given resource_type

        Arguments:
            resource_type (str): name of a resource type (e.g. 'Organization')
            search_param (str): searchparam of this resource type (e.g. 'address-postalcode')

        Returns:
            str: the fhirpath associated to the searchparam (e.g. 'address.postalCode')
        """  # noqa
        fhirpath = self.searchparameters.searchparam_to_fhirpath(search_param, resource_type)

        if fhirpath and resource_type != "all":
            params = fhirpath.split(" | ")
            filtered_params = []
            for param in params:
                if resource_type in param:
                    filtered_params.append(param)
            fhirpath = " | ".join(filtered_params)

            if len(filtered_params) == 0:
                return ValueError(
                    f"There was an error while filtrating {fhirpath} on "
                    f"resource {resource_type}"
                )
        return fhirpath

    def build_searchparameters(self) -> SearchParameters:
        """builds an instance of SearchParameters storing all the possible searchparameters
        (instance of SearchParameter) whose information comes from a bundle composed only of
        FHIR resources of type SearchParameter according to the following process:

        1. Retrieves information of interest in each instance of the bundle. For each instance
            of the bundle are retrieved: the code, the expression (=fhirpath) and the base
            (=the types of resources on which these fhirpaths can be applied)
        2. With these 3 pieces of information a SearchParameter object is created
        3. SearchParameter objects are stored in a SearchParameters object.

        Returns:
            SearchParameters: instance described above
        """  # noqa
        bundle = self._get_from_file(self.path, self.searchparameters_filename)

        resources = [resource["resource"] for resource in bundle["entry"]]

        search_parameters = SearchParameters()
        for resource in resources:
            if "expression" in resource:
                search_parameters.add(
                    SearchParameter(
                        code=resource["code"],
                        fhirpath=resource["expression"],
                        resource_types=resource["base"],
                    )
                )

        return search_parameters

    def _get_from_file(self, path: str, filename: str) -> dict:
        """Get a json (dict) from a file

        Arguments:
            path (str): path to the folder containing the filename
            filename (str): filename of the json

        Returns:
            dict: dict containing the json
        """
        with open(os.path.join(path, filename)) as json_file:
            file_dict = json.load(json_file)
        return file_dict
