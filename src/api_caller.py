import objectpath
import pandas as pd
import requests
import json
import types
import logging


class CallApi:
    """generic class that manages the sending and receiving of a url request to a FHIR API.
    """

    def __init__(self, url: str):
        self.url = url
        self.status_code = None
        self.results = None
        self.next_url = None
        self.get_response(self.url)

    def get_response(self, url: str):
        """sends the request and stores the elements of the response

        Arguments:
            url {str} -- url of the request
        """
        response = requests.get(url)
        self.status_code = response.status_code
        try:
            self.results = response.json()["entry"]
        except KeyError as e:
            # add things to understand why
            logging.info(f"Got a KeyError - There's no {e} key in the json data we received.")
        try:
            self.next_url = None
            for relation in response.json()["link"]:
                if relation["relation"] == "next":
                    self.next_url = relation["url"]
                    break
        except KeyError as e:
            # add things to understand why
            logging.info(f"Got a KeyError - There's no {e} key in the json data we received.")

    def get_next(self):
        """retrieves the responses contained in the following pages
        """
        if self.next_url:
            self.get_response(self.next_url)
        else:
            logging.info("There is no more pages")


class ApiGetter(CallApi):
    """class that manages the sending and receiving of a url request to a FHIR API and then transforms the answer into a tabular format
    """

    def __init__(self, url: str, elements: dict, main_resource_alias: str):
        CallApi.__init__(self, url)
        self.main_resource_alias = main_resource_alias
        self.elements = elements
        self.expressions = dict()
        self._get_element_at_root()
        self._get_element_after_resource()
        self.data = self._init_data()
        self._get_data()

    def display_data(self) -> pd.DataFrame:
        """transforms the collected data into a dataframe

        Returns:
            pd.DataFrame -- collected data into a dataframe
        """
        df = pd.DataFrame(self.data)
        return df

    def get_all(self):
        """collects all the data corresponding to the initial url request by calling the following pages
        """
        while self.next_url:
            self.get_next()

    def get_next(self):
        """retrieves the responses contained in the following pages and stores the data in data attribute
        """
        if self.next_url:
            self.get_response(self.next_url)
            self._get_data()
        else:
            logging.info("There is no more pages")

    def _get_data(self):
        """retrieves the necessary information from the json instance of a resource and stores it in the data attribute
        """
        dico_ressources = self._resources_to_tree()
        for ressource_tree in dico_ressources[self.main_resource_alias]:
            for element, search in self.expressions.items():
                # logging.info(f"search: {search}")
                item = ressource_tree.execute(search)
                if isinstance(item, types.GeneratorType):
                    item = list(item)
                self.data[element].append(item)

    def _resources_to_tree(self) -> dict:
        """transforms json instances of recovered resources into an objectpath.Tree

        Returns:
            dict -- dictionary containing these objectpath.Tree
        """
        dico_ressources = defaultdict(list)
        for rsc in self.results:
            rsc = objectpath.Tree(rsc)
            # type_resource = rsc.execute("$.resource.resourceType")
            # assert type_resource == self.graph.resources_alias_info[self.main_resource_alias]["resource_type"]
            dico_ressources[self.main_resource_alias].append(rsc)
        return dico_ressources

    def _init_data(self) -> dict:
        """generation of a dictionary whose keys correspond to expressions (column name) and the value to an empty list

        Returns:
            dict -- dictionary described above
        """
        data = dict()
        for elem in self.expressions.keys():
            data[elem] = []
        return data

    def _get_element_at_root(self):
        """transforms the element to be retrieved at the root level (in elements attribute) in the json file into the corresponding objectpath expression. The result is stored in expression attribute
        """
        elements_at_root = self.elements["aditionnal_root"]
        for element in elements_at_root:
            self.expressions[element] = f"$.{element}"

    def _get_element_after_resource(self):
        """transforms the element to be retrieved at the resource level (in elements attribute) in the json file into the corresponding objectpath expression. The result is stored in expression attribute
        """
        elements_after_resource = (
            self.elements["aditionnal_ressource"]
            + self.elements["select"]
            + self.elements["where"]
            + self.elements["join"]
        )
        for element in elements_after_resource:
            self.expressions[element] = f"$.resource.{element}"
