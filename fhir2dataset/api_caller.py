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


def concat_cell(dataset, cols_name, element):
    # column of one row, this single cell is of the same type as element.value, i.e. a list
    column = [element.value]
    dataset.append(column)
    cols_name.append(element.col_name)
    return dataset, cols_name


def concat_col(dataset, cols_name, element):
    for index, value in enumerate(element.value):
        # column of one row, this single cell is of the same type as value
        column = [value]
        dataset.append(column)
        cols_name.append(f"{element.col_name}_{index}")
    return dataset, cols_name


def concat_row(dataset, cols_name, element):
    # column of x=len(element.value) rows
    column = element.value
    dataset.append(column)
    cols_name.append(element.col_name)
    return dataset, cols_name


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
            if response.json()["total"] == 0:
                # no resources match the request
                self.results = {}
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
        elements_empty = asdict(self.elements)
        if self.results == {}:
            columns = [element.col_name for element in self.elements.elements]
            self.df = pd.DataFrame(columns=columns)
        else:
            for json_resource in self.results:

                data_dict = multiple_search_dict([json_resource["resource"]], elements_empty)[
                    0
                ]  # because there is only one resource
                elements = from_dict(data_class=Elements, data=data_dict)
                df = self._flatten_item_results(elements)
                self.df = pd.concat([self.df, df])

    @timing
    def _flatten_item_results(self, elements: Type[Elements]):
        """creates the tabular version of the elements given as input argument.
        For each element of elements, at least one column is added according to the following process.
        1. The first step is to reproduce the type of concatenation desired for each element
        If the concatenation type of the element is:
            * cell: a single column is created with a single row. The single cell is therefore of the same type of element.value, i.e. a list.
            * row: a single column is created and creates a row for each element in the element.value list.
            * col: len(element.value) column are created. Each column contains a single cell composed of an element from the element.value list.

        2. The second step is to produce the product of all possible combinations between columns.
        For example, if at the end of step 1, the table is : 
        Col_1 | Col_2 | Col_3
        pat_1 | Pete  | Ginger
        pat_1 | P.    | Ginger
              | Peter | G.

        The table resulting from step 2 will be : 
        Col_1 | Col_2 | Col_3
        pat_1 | Pete  | Ginger
        pat_1 | Pete  | G.
        pat_1 | P.    | Ginger
        pat_1 | P.    | G.
        pat_1 | Peter | Ginger
        pat_1 | Peter | G.

        Args:
            elements (fhir2dataset.Elements): instance of elements

        Returns:
            pd.DataFrame: resulting dataframe
        """  # noqa
        cols_name = []
        dataset = []

        for element in elements.elements:
            MAPPING_CONCAT[element.concat_type](dataset, cols_name, element)

        df = pd.DataFrame(list(product(*dataset)), columns=cols_name)
        return df

    def _init_data(self) -> dict:
        """generation of a dictionary whose keys correspond to the column name and the value to an empty list

        Returns:
            dict -- dictionary described above
        """  # noqa
        data = dict()
        for element in self.elements.elements:
            data[element.col_name] = []
        return pd.DataFrame(data)
