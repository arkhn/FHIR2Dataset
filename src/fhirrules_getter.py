import os
import json
import objectpath
import logging


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
        capabilitystatement_filename="CapabilityStatement.json",
        searchparameters_filename="SearchParameters.json",
    ):
        """
        Keyword Arguments:
            path {str} -- path to the folder containing capabilitystatement_filename and searchparameters_filename files (default: {None})
            capabilitystatement_filename {str} -- filename of a json that contains a resource of type CapabilityStatement (default: {"CapabilityStatement.json"})
            searchparameters_filename {str} -- filename of a json that contains a resource of type SearchParameters  (default: {"SearchParameters.json"})
        """

        self.capabilitystatement = self._get_from_file(
            path=path, filename=capabilitystatement_filename
        )
        self.searchparameters = self._get_from_file(path=path, filename=searchparameters_filename)

        self.possible_references = self._get_rev_include_possibilities()
        self.searchparam_to_element = self._get_searchparam_to_element()

    def resourcetype_searchparam_to_element(self, resource_type: str, search_param: str):
        """retrieves the expression that allows to retrieve the element that is the object of a searchparam in a json instance (after the 'resource' key) of a resource of a certain type

        Arguments:
            resource_type {str} -- name of a resource type (e.g. 'Organization')
            search_param {str} -- name of a searchparam of this resource type (e.g. 'address-postalcode')

        Returns:
            str -- the expression for retrieving the element that is the subject of the searchparam (e.g. 'address.postalCode')
        """
        try:
            return self.searchparam_to_element[resource_type][search_param]["expression"]
        except:
            logging.info(f"There is no such searchparam")
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
                try:
                    list_expression = expression_search_param.split(" | ")
                    find = False
                    for exp in list_expression:
                        exp_split = exp.split(".")
                        if resource_type == exp_split[0]:
                            find = True
                            expression = ".".join(exp_split[1:])
                        elif resource_type in exp_split[0]:
                            # speacial cases : CodeableConcept, Quantity etc
                            find = True
                            exp_split = ".".join(exp_split[1:])
                            expression = exp_split.split(" ")[0]
                            logging.info(f"\nexpression: {expression}\n")
                    if not find:
                        logging.info(
                            f"\nNot found"
                            f"\nresource_type: {resource_type}"
                            f"\nname_search_param: {name_search_param}"
                            f"\nlist_expression: \n{list_expression}"
                            f"\nresource_tree:\n {resource}\n"
                        )
                    dict_searchparam[resource_type][name_search_param] = {
                        "expression": expression,
                    }
                except:
                    logging.info(f"resource_tree:\n {resource}\n")

        return dict_searchparam

    def _get_rev_include_possibilities(self) -> dict:
        """Builds a dictionary that will indicate for each type of resource which are its mother resources (revinclude) and its daughter resources (include).
        
        Returns:
            dict -- a dictionary as described above
        """
        dict_reference = dict()
        for resource in self.capabilitystatement["resource"]["rest"][0][
            "resource"
        ]:  # check the 0 , we could have several
            type = resource["type"]
            dict_reference[type] = dict()
            if "searchRevInclude" in resource:
                dict_reference[type]["searchRevInclude"] = resource["searchRevInclude"]
            if "searchInclude" in resource:
                dict_reference[type]["searchInclude"] = resource["searchInclude"]
        return dict_reference

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

    # def _get_capabilitystatement_from_api(self) -> dict:
    #     """Get the CapabilityStatement from the base

    #     Returns:
    #         dict --  dict object containing a CapabilityStatement
    #         resource
    #     """
    #     url = f"{self.fhir_api_url}/CapabilityStatement?"
    #     response = requests.get(url)
    #     # 0 by default but we must investigate how to chose the right
    #     # CapabilityStatement ?
    #     capabilitystatement = response.json()["entry"][0]
    #     return capabilitystatement
