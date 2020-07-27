import pandas as pd
import requests
import logging
from itertools import product
from typing import Type
from dataclasses import asdict
from dacite import from_dict

from fhir2dataset.timer import timing
from fhir2dataset.fhirpath import multiple_search_dict
from fhir2dataset.data_class import Elements

logger = logging.getLogger(__name__)


def concat_cell(dataset, cols, element):
    dataset.append([element.value])
    cols.append(element.col_name)
    return dataset, cols


def concat_col(dataset, cols, element):
    for index, value in enumerate(element.value):
        dataset.append([value])
        cols.append(f"{element.col_name}_{index}")
    return dataset, cols


def concat_row(dataset, cols, element):
    dataset.append(element.value)
    cols.append(element.col_name)
    return dataset, cols


MAPPING_CONCAT = {"cell": concat_cell, "col": concat_col, "row": concat_row}


class CallApi:
    """generic class that manages the sending and receiving of a url request to a FHIR API.
    """

    @timing
    def __init__(self, url: str, token: str = None):
        self.url = url
        self.status_code = None
        self.results = None
        self.next_url = url
        self.auth = BearerAuth(token)

    @timing
    def get_response(self, url: str):
        """sends the request and stores the elements of the response

        Arguments:
            url {str} -- url of the request
        """
        # TODO : optimize count and paging
        # count = self._get_count(url)
        # if count == 0:
        #     logger.warning(f"there is 0 matching resources for {url}")
        # if url[-1] == "?":
        #     url = f"{url}_count={count}"
        # else:
        #     url = f"{url}&_count={count}"
        response = self._get_bundle_response(url)
        self.status_code = response.status_code
        try:
            self.results = response.json()["entry"]
        except KeyError as e:
            logger.info(f"Got a KeyError - There's no {e} key in the json data we received.")
            logger.debug(f"status code of KeyError response:\n{response.status_code}")
            logger.debug(f"content of the KeyError response:\n{response.content}")
        try:
            self.next_url = None
            for relation in response.json()["link"]:
                if relation["relation"] == "next":
                    self.next_url = relation["url"]
                    break
        except KeyError as e:
            logger.info(f"Got a KeyError - There's no {e} key in the json data we received.")
            logger.debug(f"status code of KeyError response:\n{response.status_code}")
            logger.debug(f"content of the KeyError response:\n{response.content}")

    @timing
    def _get_count(self, url):
        # the retrieval of the number of results is not necessary if the FHIR api supports
        # pagination
        # -> to be deleted
        if url[-1] == "?":
            url_number = f"{url}_summary=count"
        else:
            url_number = f"{url}&_summary=count"
        response = requests.get(url_number, auth=self.auth)
        logger.info(f"Get {url_number}")
        try:
            count = min(response.json()["total"], 10000)
        except KeyError as e:
            logger.info(f"Got a KeyError - There's no {e} key in the json data we received.")
            logger.warning(f"status code of failing response:\n{response.status_code}")
            logger.warning(f"content of the failing response:\n{response.content}")
            raise
        except ValueError:
            logger.warning(f"status code of failing response:\n{response.status_code}")
            logger.warning(f"content of the failing response:\n{response.content}")
            raise
        except ValueError:
            logger.warning(f"status code of failing response:\n{response.status_code}")
            logger.warning(f"content of the failing response:\n{response.content}")
            raise
        return count

    @timing
    def _get_bundle_response(self, url):
        logger.info(f"Get {url}")
        return requests.get(url, auth=self.auth)

    @timing
    def get_next(self):
        """retrieves the responses contained in the following pages
        """
        if self.next_url:
            self.get_response(self.next_url)
        else:
            logger.info("There is no more pages")


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        if self.token:
            r.headers["Authorization"] = "Bearer " + self.token
        return r


class ApiGetter(CallApi):
    """class that manages the sending and receiving of a url request to a FHIR API and then transforms the answer into a tabular format

    Attributes:
        elements (Elements): instance of the FHIR2Dataset Elements class that allows to list all the elements that need to be retrieved from the bundles returned in response to the request url
        df (pd.DataFrame): dataframe containing the elements to be recovered in tabular format
    """  # noqa

    @timing
    def __init__(
        self, url: str, elements: Type[Elements], token: str = None,
    ):
        CallApi.__init__(self, url, token)
        self.elements = elements
        self.df = self._init_data()

    @timing
    def get_all(self):
        """collects all the data corresponding to the initial url request by calling the following pages
        """  # noqa
        while self.next_url:
            self.get_next()

    @timing
    def get_next(self):
        """retrieves the responses contained in the following pages and stores the data in data attribute
        """  # noqa
        if self.next_url:
            self.get_response(self.next_url)
            self._get_data()
        else:
            logger.info("There is no more pages")

    @timing
    def _get_data(self):
        """retrieves the necessary information from the json instance of a resource and stores it in the data attribute
        """  # noqa
        data = self.df
        elements_empty = asdict(self.elements)
        for json_resource in self.results:

            data_dict = multiple_search_dict([json_resource["resource"]], elements_empty)[
                0
            ]  # because there is only one resource
            elements = from_dict(data_class=Elements, data=data_dict)
            df = self._flatten_item_results(elements)
            data = pd.concat([data, df])
        self.df = data

    @timing
    def _flatten_item_results(self, elements: Type[Elements]):
        cols = []
        dataset = []

        for element in elements.elements:
            MAPPING_CONCAT[element.concat_type](dataset, cols, element)

        df2 = pd.DataFrame(list(product(*dataset)), columns=cols)
        return df2

    def _init_data(self) -> dict:
        """generation of a dictionary whose keys correspond to the column name and the value to an empty list

        Returns:
            dict -- dictionary described above
        """  # noqa
        data = dict()
        for col_name in [element.col_name for element in self.elements.elements]:
            data[col_name] = []
        return pd.DataFrame(data)
