import os
import json
import objectpath
import logging
from collections import defaultdict
from functools import lru_cache

from fhir2dataset.timer import timing
from fhir2dataset.fhirpath import multiple_search_dict

logger = logging.getLogger(__name__)

DEFAULT_METADATA_DIR = "metadata"


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
        self.searchparameters = self._get_from_file(path=path, filename=searchparameters_filename)
        self.searchparam_to_element = self._get_searchparam_to_element()

    @timing
    @lru_cache(maxsize=200)
    def resourcetype_searchparam_to_element(self, resource_type: str, search_param: str):
        """retrieves the fhirpath that allows to retrieve the element that is the object of a searchparam in a json instance (after the 'resource' key) of a resource of a certain type

        Arguments:
            resource_type {str} -- name of a resource type (e.g. 'Organization')
            search_param {str} -- name of a searchparam of this resource type (e.g. 'address-postalcode')

        Returns:
            str -- the fhirpath for retrieving the element that is the subject of the searchparam (e.g. 'address.postalCode')
        """  # noqa
        try:
            return self.searchparam_to_element[resource_type][search_param]
        except KeyError:
            logger.warning(f"The searchparam '{search_param}' doesn't exist in the rules")
            return None

    @timing
    def _get_searchparam_to_element(self) -> dict:
        """builds a dictionary storing for each resource the fhirpath corresponding to each searchparameter (e.g. {'Organization': {'address-postalcode':'address.postalCode'}})

        Returns:
            dict -- a dictionary as described above
        """  # noqa
        dict_searchparam = defaultdict(dict)
        fhirpaths = ["SearchParameter.code", "SearchParameter.expression", "SearchParameter.base"]
        resources = [resource["resource"] for resource in self.searchparameters["entry"]]
        results = multiple_search_dict(resources, fhirpaths)
        for idx, result in enumerate(results):
            if result[1]:
                for resource_type in result[2]:
                    dict_searchparam[resource_type][result[0][0]] = result[1][0]
            else:
                logger.warning(
                    f"\nthe instance of SearchParamater named {result[0]}"
                    f" has no fhirpath associated"
                )
                logger.debug(f"{resources[idx]}\n")
        return dict_searchparam

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
