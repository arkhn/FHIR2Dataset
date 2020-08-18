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


class Response:
    """class that contains the data retrieves from an url
    """

    def __init__(self):
        self.status_code = None
        self.results = None
        self.next_url = None


class CallApi:
    """generic class that manages the sending and receiving of a url request to a FHIR API.
    """

    @timing
    def __init__(self, url: str, token: str = None):
        self.url = url
        self.total = None
        self.auth = BearerAuth(token)

    @timing
    def get_response(self, url: str):
        """sends the request and stores the elements of the response

        Arguments:
            url {str} -- url of the request
        """
        if self.total is None:
            self.total = self._get_count(url)
            logger.info(f"there is {self.total} matching resources for {url}")
        if self.total != 0:
            # response_url contains the data returned by url
            response_url = Response()
            response = self._get_bundle_response(url)
            response_url.status_code = response.status_code
            if "entry" in response.json():
                # if no resources match the request, response_url.results = None
                logger.debug(f"status code of KeyError response:\n{response.status_code}")
                logger.debug(f"content of the KeyError response:\n{response.content}")
                response_url.results = response.json()["entry"]
                links = response.json().get("link", [])
                next_page = [l["url"] for l in links if l["relation"] == "next"]
                if len(next_page) > 0:
                    response_url.next_url = next_page[0]
                else:
                    logger.info("no next url was found")
            else:
                logger.info(f"Got a KeyError - There's no entry key in the json data we received.")
        else:
            response_url = Response()
        return response_url

    @timing
    def _get_count(self, url):
        if url[-1] == "?":
            url_number = f"{url}_summary=count"
        else:
            url_number = f"{url}&_summary=count"
        logger.info(f"Get {url_number}")
        response = requests.get(url_number, auth=self.auth)
        count = response.json().get("total")
        if count is None:
            logger.warning(f"status code of failing response:\n{response.status_code}")
            logger.warning(f"content of the failing response:\n{response.content}")
        return count

    @timing
    def _get_bundle_response(self, url):
        logger.info(f"Get {url}")
        return requests.get(url, auth=self.auth)


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
        next_url = self.url
        while next_url:
            next_url = self.get_next(next_url)

    @timing
    def get_next(self, next_url):
        """retrieves the responses contained in the following pages and stores the data in data attribute
        """  # noqa
        if next_url:
            response = self.get_response(next_url)
            next_url = self._get_data(response)
            return next_url
        else:
            logger.info("There is no more pages")
            return None

    @timing
    def _get_data(self, response: Type[Response]):
        """retrieves the necessary information from the json instance of a resource and stores it in the data attribute
        """  # noqa
        elements_empty = asdict(self.elements)
        if not response.results:
            columns = [element.col_name for element in self.elements.elements]
            df = pd.DataFrame(columns=columns)
            self.df = pd.concat([self.df, df])
            logger.info(
                "the current page doesnt have an entry keyword, therefore an empty df is created"
            )
        else:
            data_dicts = multiple_search_dict(
                [json_resource["resource"] for json_resource in response.results], elements_empty
            )
            for data_dict in data_dicts:
                elements = from_dict(data_class=Elements, data=data_dict)
                df = self._flatten_item_results(elements)
                self.df = pd.concat([self.df, df])
        return response.next_url

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
