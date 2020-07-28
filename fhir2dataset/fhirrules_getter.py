import os
import json
import logging
from functools import lru_cache
from dataclasses import asdict
from dacite import from_dict

from fhir2dataset.timer import timing
from fhir2dataset.fhirpath import multiple_search_dict
from fhir2dataset.data_class import SearchParameters, SearchParameter, Elements, Element

logger = logging.getLogger(__name__)

DEFAULT_METADATA_DIR = "metadata"

MAPPING_SEARCHPARAMS = {
    "code": lambda search_param, element_value: setattr(
        search_param, "code", next(iter(element_value), None)
    ),
    "expression": lambda search_param, element_value: setattr(
        search_param, "fhirpath", next(iter(element_value), None)
    ),
    "base": lambda search_param, element_value: setattr(
        search_param, "resource_types", element_value
    ),
}


class FHIRRules:
    """Class storing rules specific to the FHIR syntax and/or the FHIR API used

    Attributes:
        possible_references {dict} -- dictionary storing searchparameters that can be used from a resource after an _include or _revinclude parameter
        searchparam_to_element {dict} -- dictionary storing for each resource the fhirpath corresponding to each searchparameter (e.g. {'Organization': {'address-postalcode': 'address.postalCode'}})
        capabilitystatement {dict} -- an instance json of a CapabilityStatement resource
        searchparameters {dict} -- an instance json of a SearchParameters resource
    """  # noqa

    @timing
    def __init__(
        self,
        path: str = None,
        fhir_api_url: str = None,
        searchparameters_filename: str = "SearchParameters.json",
    ):
        """
        Keyword Arguments:
            fhir_api_url {str} -- The Service Base URL (e.g. http://hapi.fhir.org/baseR4/) (default: {None})
            path {str} -- path to the folder containing capabilitystatement_filename and searchparameters_filename files (default: {None})
            searchparameters_filename {str} -- filename of a json that contains a resource of type SearchParameters  (default: {"SearchParameters.json"})
        """  # noqa
        self.fhir_api_url = fhir_api_url
        if not path:
            path = os.path.join(os.path.dirname(__file__), DEFAULT_METADATA_DIR)
        self.path = path
        self.searchparameters_filename = searchparameters_filename
        self.searchparameters = self._get_searchparameters()

    @timing
    @lru_cache(maxsize=200)
    def searchparam_to_fhirpath(self, search_param: str, resource_type: str = "all"):
        """retrieves the fhirpath that allows to retrieve the element that is the object of a searchparam in a json instance (after the 'resource' key) of a resource of a certain type

        Arguments:
            resource_type {str} -- name of a resource type (e.g. 'Organization')
            search_param {str} -- name of a searchparam of this resource type (e.g. 'address-postalcode')

        Returns:
            str -- the fhirpath for retrieving the element that is the subject of the searchparam (e.g. 'address.postalCode')
        """  # noqa
        try:
            return self.searchparameters.searchparam_to_fhirpath(search_param, resource_type)
        except KeyError:
            logger.warning(f"The searchparam '{search_param}' doesn't exist in the rules")
            return None

    @timing
    def _get_searchparameters(self) -> dict:
        """builds an instance of SearchParameters storing all the possible searchparameters (instance of SearchParameter) whose information comes from a bundle composed only of FHIR resources of type SearchParameter according to the following process:
        1. Retrieves information of interest in each instance of the bundle. For each instance of the bundle are retrieved: the code, the expression (=fhirpath) and the base (=the types of resources on which these fhirpaths can be applied)
        2. With these 3 pieces of information a SearchParameter object is created
        3. SearchParameter objects are stored in a SearchParameters object.

        Returns:
            SearchParameters -- instance described above
        """  # noqa
        bundle = self._get_from_file(self.path, self.searchparameters_filename)
        elements_empty = Elements(
            elements=[
                Element(col_name="code", fhirpath="SearchParameter.code",),
                Element(col_name="expression", fhirpath="SearchParameter.expression",),
                Element(col_name="base", fhirpath="SearchParameter.base",),
            ]
        )
        elements_empty = asdict(elements_empty)
        resources = [resource["resource"] for resource in bundle["entry"]]
        raw_list_elements = multiple_search_dict(resources, elements_empty)
        search_parameters = SearchParameters()
        for idx, raw_elements in enumerate(raw_list_elements):
            elements = from_dict(data_class=Elements, data=raw_elements)
            search_param = SearchParameter()
            for element in elements.elements:
                MAPPING_SEARCHPARAMS[element.col_name](search_param, element.value)
            if search_param.fhirpath and search_param.resource_types:
                search_parameters.add(search_param)
            else:
                logger.warning(
                    f"\nthe instance of SearchParameter named "
                    f"{search_param.code}"
                    f" has no fhirpath associated"
                )
                logger.debug(f"{resources[idx]}\n")
        return search_parameters

    @timing
    def _get_from_file(self, path: str, filename: str) -> dict:
        """Get a json (dict) from a file

        Arguments:
            path {str} -- path to the folder containing the filename
            filename {str} -- filename of the json

        Returns:
            dict -- dict containing the json
        """
        with open(os.path.join(path, filename)) as json_file:
            file_dict = json.load(json_file)
        return file_dict
