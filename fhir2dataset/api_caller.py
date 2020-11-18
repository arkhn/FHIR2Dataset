import numpy as np
import pandas as pd
import requests
import logging
from itertools import product
import multiprocessing
from typing import Type

# from fhir2dataset.fhirpath import fhirpath_processus_tree
from fhir2dataset.data_class import Elements

logger = logging.getLogger(__name__)

PAGE_SIZE = 300  # Return maximum 300 entities per query


def concat_cell(dataset, cols_name, element):
    # column of one row, this single cell is of the same type as element.value, i.e. a list
    if element.value == []:
        element.value = [None]
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


def process_function(token, url):
    """Function called by the different processes when doing parallel querying
    of the API"""
    auth = BearerAuth(token)
    response = requests.get(url, auth=auth)
    return response.json()


class Response:
    """class that contains the data retrieves from an url"""

    def __init__(self):
        self.status_code = None
        self.results = None
        self.next_url = None


class CallApi:
    """generic class that manages the sending and receiving of a url request to a FHIR API."""

    def __init__(self, url: str, token: str = None):
        self.url = url
        self.total = None
        self.auth = BearerAuth(token)
        self.parallel_requests = False

    def get_response(self, url: str):
        """sends the request and stores the elements of the response

        Arguments:
            url {str} -- url of the request
        """
        if self.total is None:
            self.total = self._get_count(url)
            logger.info(f"there is {self.total} matching resources for {url}")

        # response_url contains the data returned by url
        response_url = Response()
        if url[-1] == "?":
            url = f"{url}_count={PAGE_SIZE}"
        else:
            url = f"{url}&_count={PAGE_SIZE}"
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

        return response_url

    def process_response(self, response):
        """Put the json response in a Response object

        Arguments:
            response {dict} -- A dict with the jsonified response
        """
        # response_url contains the data returned by url
        response_url = Response()
        response_url.status_code = 200
        if "entry" in response:
            response_url.results = response["entry"]
        else:
            logger.info(f"Got a KeyError - There's no entry key in the json data we received.")
            logger.info(response)

        return response_url

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
    """class that manages the sending and receiving of a url request to a FHIR API and then
    transforms the answer into a tabular format

    Attributes:
        elements (Elements): instance of the FHIR2Dataset Elements class that allows to list
            all the elements that need to be retrieved from the bundles returned in response to
            the request url
        df (pd.DataFrame): dataframe containing the elements to be recovered in tabular format
        pbar : tqdm progress bar object
        time_frac (int): total amount of time allocated to this Api call
    """  # noqa

    def __init__(
        self, url: str, elements: Type[Elements], token: str = None, pbar=None, time_frac: int = 0
    ):
        CallApi.__init__(self, url, token)
        self.elements = elements
        self.df = self._init_data()

        self.pbar = pbar
        self.time_frac = time_frac

    def get_all(self):
        """collects all the data corresponding to the initial url request by calling the following pages"""  # noqa
        if self.total is None:
            self.total = self._get_count(self.url)
            logger.info(f"there is {self.total} matching resources for {self.url}")
            count_time = round(self.time_frac * 0.1)
            self.pbar.update(count_time)
            self.time_frac -= count_time

        if self.total == 0:
            return

        number_calls = int(np.ceil(self.total / PAGE_SIZE))

        if number_calls == 1:
            urls = [(self.auth.token, self.url)]
        else:
            urls = []
            for i in range(number_calls):
                urls.append(
                    (
                        self.auth.token,
                        f"{self.url}&_getpagesoffset={i*PAGE_SIZE}&_count={PAGE_SIZE}",
                    )
                )

        if self.parallel_requests:
            p = multiprocessing.Pool()
            responses = p.starmap(process_function, urls)
            p.close()
            self.pbar.update(self.time_frac)
        else:
            responses = []
            # time is split between all urls
            time_frac_per_url = round(self.time_frac / number_calls)
            for url in urls:
                responses.append(process_function(*url))
                self.pbar.update(time_frac_per_url)
            # fix rounding error
            self.pbar.update(self.time_frac - time_frac_per_url * number_calls)

        for response in responses:
            response = self.process_response(response)
            _ = self._get_data(response)

    def get_next(self, next_url):
        """retrieves the responses contained in the following pages and stores the data in data attribute"""  # noqa
        if next_url:
            response = self.get_response(next_url)
            next_url = self._get_data(response)
            return next_url
        else:
            logger.info("There is no more pages")
            return None

    @classmethod
    def rgetattr(cls, obj, keys):
        """
        Recursively get an element in nested dictionaries

        Example:
            >>> rgetattr(obj, ['attr1', 'attr2', 'attr3'])
            [Out] obj[attr1][attr2][attr3]

        """
        if not isinstance(obj, list):
            if len(keys) == 1:
                return obj[keys[0]]
            else:
                first_key, *keys = keys
                return cls.rgetattr(obj[first_key], keys)
        else:
            return [cls.rgetattr(o, keys) for o in obj]

    def _get_data(self, response: Type[Response]):
        """retrieves the necessary information from the json instance of a resource and stores it in the data attribute"""  # noqa
        if not response.results:
            columns = [element.col_name for element in self.elements.elements]
            df = pd.DataFrame(columns=columns)
            self.df = pd.concat([self.df, df])
            logger.info(
                "the current page doesnt have an entry keyword, therefore an empty df is created"
            )
        else:
            columns = [element.col_name for element in self.elements.elements]
            filtered_resources = []
            for json_resource in response.results:
                resource = json_resource["resource"]
                data_items = []
                for element in self.elements.elements:
                    fhirpath = element.fhirpath.replace("(", "").replace(")", "")
                    sub_paths = fhirpath.split(".")
                    if len(sub_paths) > 0 and sub_paths[0] == resource["resourceType"]:
                        try:
                            # Try to get recursively the keys from sub_paths[1:]
                            data_item = ApiGetter.rgetattr(resource, sub_paths[1:])
                        except KeyError:
                            data_item = None
                    elif fhirpath == "id":
                        data_item = resource["id"]
                    else:
                        raise ValueError(f"Invalid fhirpath {fhirpath}")
                    data_items.append(data_item)

                filtered_resources.append(data_items)

                # elements = self.elements.elements.copy()
                # data_array = fhirpath_processus_tree(self.elements.forest_dict, resource)
                # for element_value, element in zip(data_array, elements):
                #     element.value = element_value
                # df = self._flatten_item_results(elements)
            df = pd.DataFrame(filtered_resources, columns=columns)
            self.df = pd.concat([self.df, df])

        return response.next_url

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

        for element in elements:
            MAPPING_CONCAT[element.concat_type](dataset, cols_name, element)

        df = pd.DataFrame(list(product(*dataset)), columns=cols_name)
        return df

    def _init_data(self) -> dict:
        """generation of a dictionary whose keys correspond to the column name and the value to an empty list

        Returns:
            dict -- dictionary described above
        """  # noqa
        data = {}
        for element in self.elements.elements:
            data[element.col_name] = []
        return pd.DataFrame(data)
