import os
import json
import objectpath
import logging
import requests

logger = logging.getLogger(__name__)

DEFAULT_METADATA_DIR = "metadata"


class FHIRRules:
    """Class storing rules specific to the FHIR syntax and/or the FHIR API used

    Attributes:
        possible_references {dict} -- dictionary storing searchparameters that can be used from a resource after an _include or _revinclude parameter
        searchparam_to_element {dict} -- dictionary storing for each resource the expression corresponding to each searchparameter (e.g. {'Organization': {'address-postalcode': {'expression': 'address.postalCode'}}})
        capabilitystatement {dict} -- an instance json of a CapabilityStatement resource
        searchparameters {dict} -- an instance json of a SearchParameters resource
    """

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
        """
        self.fhir_api_url = fhir_api_url
        if not path:
            path = os.path.join(os.path.dirname(__file__), DEFAULT_METADATA_DIR)
        self.searchparameters = self._get_from_file(
            path=path, filename=searchparameters_filename
        )
        self.searchparam_to_element = self._get_searchparam_to_element()

    def resourcetype_searchparam_to_element(
        self, resource_type: str, search_param: str
    ):
        """retrieves the expression that allows to retrieve the element that is the object of a searchparam in a json instance (after the 'resource' key) of a resource of a certain type

        Arguments:
            resource_type {str} -- name of a resource type (e.g. 'Organization')
            search_param {str} -- name of a searchparam of this resource type (e.g. 'address-postalcode')

        Returns:
            str -- the expression for retrieving the element that is the subject of the searchparam (e.g. 'address.postalCode')
        """
        try:
            return self.searchparam_to_element[resource_type][search_param][
                "expression"
            ]
        except:
            logger.warning(
                f"The searchparam '{search_param}' doesn't exist in the rules"
            )
            return None

    def _get_searchparam_to_element(self) -> dict:
        """builds a dictionary storing for each resource the expression corresponding to each searchparameter (e.g. {'Organization': {'address-postalcode': {'expression': 'address.postalCode'}}})

        Returns:
            dict -- a dictionary as described above
        """
        dict_searchparam = dict()
        for resource in self.searchparameters["entry"]:
            resource_tree = objectpath.Tree(resource)
            name_search_param = resource_tree.execute("$.resource.code")
            expression_search_param = resource_tree.execute("$.resource.expression")
            # xpath_search_param = resource_tree.execute("$.resource.xpath")
            for resource_type in resource_tree.execute("$.resource.base"):
                if resource_type not in dict_searchparam:
                    dict_searchparam[resource_type] = dict()
                if expression_search_param:
                    list_expression = expression_search_param.split(" | ")
                    find = False
                    for exp in list_expression:
                        exp_split = exp.split(".")
                        if resource_type == exp_split[0]:
                            find = True
                            expression = ".".join(exp_split[1:])
                        elif resource_type in exp_split[0]:
                            # special cases : CodeableConcept, Quantity etc
                            find = True
                            exp_split = ".".join(exp_split[1:])
                            expression = exp_split.split(" ")[0]
                            logger.debug(
                                f"\nthe searchpram '{name_search_param} is associated with this FHIRpath '{expression}'\n"
                            )
                    if not find:
                        logger.warning(
                            f"\nthe fhirpath associated to the instance of SearchParamater "
                            f"named '{name_search_param}' wasn't found for the resource_type "
                            f"'{resource_type}''"
                        )
                        logger.debug(
                            f"the list of firpath associated with this SearchParamater is "
                            f"{list_expression}"
                            f"the json associated is :\n {resource}\n"
                        )
                    dict_searchparam[resource_type][name_search_param] = {
                        "expression": expression,
                    }
                else:
                    logger.warning(
                        f"\nthe instance of SearchParamater named '{name_search_param}' has no expression associated"
                    )
                    logger.debug(f"{resource}\n")
        return dict_searchparam

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
