import logging
import multiprocessing
import pprint
from json import JSONDecodeError
from typing import List, Optional

import numpy as np
import pandas as pd
import requests

# from fhir2dataset.fhirpath import fhirpath_processus_tree
from fhir2dataset.data_class import Elements
from fhir2dataset.tools.progressbar import progressbar

logger = logging.getLogger(__name__)

PAGE_SIZE = 100  # Return maximum 300 entities per query


# def concat_cell(dataset, cols_name, element):
#     # column of one row, this single cell is of the same type as element.value, i.e. a list
#     if element.value == []:
#         element.value = [None]
#     column = [element.value]
#     dataset.append(column)
#     cols_name.append(element.col_name)
#     return dataset, cols_name
#
#
# def concat_col(dataset, cols_name, element):
#     for index, value in enumerate(element.value):
#         # column of one row, this single cell is of the same type as value
#         column = [value]
#         dataset.append(column)
#         cols_name.append(f"{element.col_name}_{index}")
#     return dataset, cols_name
#
#
# def concat_row(dataset, cols_name, element):
#     # column of x=len(element.value) rows
#     column = element.value
#     dataset.append(column)
#     cols_name.append(element.col_name)
#     return dataset, cols_name
#
#
# MAPPING_CONCAT = {"cell": concat_cell, "col": concat_col, "row": concat_row}


def process_function(token, url):
    """
    Make a call to a remote API.
    Function called by the different processes when doing parallel querying of the API
    """
    auth = BearerAuth(token)
    response = requests.get(url, auth=auth)
    return response.json()


class Response:
    """class that contains the data retrieves from an url"""

    def __init__(self, total: int = None, results: List = None, next_url: str = None):
        self.total: Optional[int] = total
        self.results: List = results
        self.next_url: Optional[str] = next_url


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        if self.token:
            r.headers["Authorization"] = self.token
        return r


class ApiCall:
    """Generic class that execute a specific url request to a FHIR API.
    This class also fixes urls that might be broken, and handle errors
    from the API.

    Attributes:
        url (str): the url of the api to call
        auth (BearerAuth): (optional) a bearer toke if necessary
    """  # noqa

    def __init__(self, url: str, token: str = None):
        self.url = url
        self.auth = BearerAuth(token)

    @progressbar
    def _get_response(self, url: str) -> Response:
        logger.info(f"Get {url}")

        url = self.__fix_url(url)

        response = requests.get(url, auth=self.auth)

        failed = False
        try:
            response_content = response.json()
            # One of these entries should be found
            if "entry" not in response_content and "total" not in response_content:
                failed = True
        except JSONDecodeError:
            failed = True

        if not failed:
            results = response_content.get("entry")
            links = response_content.get("link", [])
            next_pages = [link["url"] for link in links if link["relation"] == "next"]

            response = Response(
                total=response_content.get("total", 0),
                results=results,
                next_url=next_pages[0] if next_pages and results else None,
            )
            return response
        else:
            raise ValueError(
                f"Request: {url}\n"
                f"Status code of failing response: {response.status_code}\n"
                f"Content of the failing response:\n{pprint.pformat(response.__dict__)}"
            )

    def _get_count(self, url: str) -> int:
        url_count = f"{url}?_summary=count"
        logger.info(f"Get {url_count}")

        response = self._get_response(url_count)
        return response.total

    def _fix_next_url(self, next_url: str) -> str:
        """Apply a set of fixes for the next_url of the Arkhn Api"""
        # FIXME: Not needed anymore now that we use hapi.
        # FIXME: Remove this function
        # if "arkhn" in next_url:
        #     # Enforce that the base URL is not changed
        #     if self.url not in next_url:
        #         next_url = re.sub(
        #             r"^(?:http:\/\/|www\.|https:\/\/)([^\/]+)",
        #             self.url,
        #             next_url,  # hackalert
        #         )

        if "_count" not in next_url:
            # Append _count info
            next_url = f"{next_url}?_count={PAGE_SIZE}"

        return next_url

    @staticmethod
    def __fix_url(url):
        """Apply a set of hot fixes on the url"""

        # Hot fix: remove noisy "%3D"
        url = url.replace("%3D", "")

        # Hot fix in syntax
        url = url.replace("/?", "?")

        # Hot fix to change several '?' in the url in 1 '?' and '&' after
        # (e.g g.co/api?a=1&b=1?c=1 becomes g.co/api?a=1&b=1&c=1

        seen = False
        clean_url = ""
        for char in url:
            if char == "?":
                if not seen:
                    seen = True
                    clean_url += "?"
                else:
                    clean_url += "&"
            else:
                clean_url += char
        url = clean_url

        return url


class ApiRequest(ApiCall):
    """Class that inherits ApiCall, and manage the Request by splitting it in different call.
    This class manages the organisation of the calls to the api and the processing of the data
    received

    Attributes:
        elements (Elements): instance of the FHIR2Dataset Elements class that allows to list
            all the elements that need to be retrieved from the bundles returned in response to
            the request url
        df (pd.DataFrame): dataframe containing the elements to be recovered in tabular format
        parallel_requests (bool) if true, perform queries in get_all() in parallel using an
            offset functionality of some FHIR Apis
        pbar : tqdm progress bar object
        bar_frac (int): total amount of time allocated to this Api call
    """  # noqa

    def __init__(
        self,
        url: str,
        elements: Elements,
        token: str = None,
        parallel_requests: bool = False,
        pbar=None,
        bar_frac: int = 0,
    ):
        ApiCall.__init__(self, url, token)
        self.elements = elements
        self.df = self._init_data()

        self.parallel_requests = parallel_requests

        self.pbar = pbar
        self.bar_frac = bar_frac
        self.number_calls = None

    def get_all(self):
        """collects all the data corresponding to the initial url request by calling the following pages"""  # noqa
        if self.number_calls is None:
            total_resources = self._get_count(self.url)
            logger.info(f"there are {total_resources} matching resources for {self.url}")
            self.number_calls = int(np.ceil(total_resources / PAGE_SIZE))

        if self.number_calls == 0:
            return self._get_data([])

        if self.parallel_requests:
            urls = []
            for i in range(self.number_calls):
                urls.append(
                    (
                        self.auth.token,
                        f"{self.url}&_getpagesoffset={i*PAGE_SIZE}&_count={PAGE_SIZE}",
                    )
                )

            p = multiprocessing.Pool()
            results = p.starmap(process_function, urls)
            p.close()
            self.pbar.update(self.bar_frac)
        else:
            results = []

            next_url = self.url
            while next_url:
                next_url = self._fix_next_url(next_url)
                response = self._get_response(next_url)
                page_results = self._get_data(response.results)

                results.append(page_results)
                next_url = response.next_url

        self._concat(results)

        return self.df

    def _get_data(self, results: List) -> pd.DataFrame:
        """Retrieves the information from the json instance of a resource that is relevant
        to the query (ie listed in self.elements) and put it in a Dataframe

        Arguments:
            results: list of json resources

        Returns:
            pd.DataFrame: with data extracted from the json resources
        """

        columns = [element.col_name for element in self.elements.elements]
        filtered_resources = []
        for json_resource in results:
            resource = json_resource["resource"]
            data_items = []
            for element in self.elements.elements:
                fhirpath = element.fhirpath.replace("(", "").replace(
                    ")", ""
                )  # TODO: analyze this: breaks .where()
                sub_paths = fhirpath.split(".")
                if len(sub_paths) > 0 and sub_paths[0] == resource["resourceType"]:
                    try:
                        # Try to get recursively the keys from sub_paths[1:]
                        data_item = ApiRequest._rgetattr(resource, sub_paths[1:])
                    except KeyError:
                        data_item = None
                elif fhirpath == "id":
                    data_item = resource["id"]
                else:
                    raise ValueError(f"Invalid fhirpath {fhirpath}")
                data_items.append(data_item)

            filtered_resources.append(data_items)

            # FIXME: Need FHIR2Dataset#96
            # elements = self.elements.elements.copy()
            # data_array = fhirpath_processus_tree(self.elements.forest_dict, resource)
            # for element_value, element in zip(data_array, elements):
            #     element.value = element_value
            # df = self._flatten_item_results(elements)
        df = pd.DataFrame(filtered_resources, columns=columns)

        # Drop duplicate columns (when you have two where clauses on a parameter)
        df = df.loc[:, ~df.columns.duplicated()]

        return df

    def _concat(self, results: List[pd.DataFrame]) -> pd.DataFrame:
        """Recursively concat the results of all the pages together

        Arguments:
            results: the list of the dataframes returned by each call

        Returns:
            pd.Dataframe: a consolidated dataframe containing all the results
        """
        self.df = pd.concat([self.df, *results]).reset_index(drop=True)
        return self.df

    @classmethod
    def _rgetattr(cls, obj, keys):
        """
        Recursively get an element in nested dictionaries

        Example:
            >>> ApiRequest._rgetattr(obj, ['attr1', 'attr2', 'attr3'])
            [Out] obj[attr1][attr2][attr3]

        """
        if not isinstance(obj, list):
            # TODO: Fix because ( ) were removed
            if keys[0].startswith("where"):
                attr, value = keys[0][5:].split("=")
                value = value.replace('"', "").replace("'", "")
                if attr in obj and obj[attr] == value:
                    keys = keys[1:]
                else:
                    return None  # FIXME: nothing should be added to a list of contacts

            if len(keys) == 0:
                return obj
            elif len(keys) == 1:
                return obj[keys[0]]
            else:
                first_key, *keys = keys
                return cls._rgetattr(obj[first_key], keys)
        else:
            return [cls._rgetattr(o, keys) for o in obj]

    # INFO: Disabled as we prefere keep lists for the moment
    # def _flatten_item_results(self, elements: Elements):
    #     """creates the tabular version of the elements given as input argument.
    #     For each element of elements, at least one column is added according to the
    #     following process.
    #     1. The first step is to reproduce the type of concatenation desired for each element
    #     If the concatenation type of the element is:
    #         * cell: a single column is created with a single row. The single cell is therefore
    #           of the same type of element.value, i.e. a list.
    #         * row: a single column is created and creates a row for each element in the
    #           element.value list.
    #         * col: len(element.value) column are created. Each column contains a single cell
    #           composed of an element from the element.value list.
    #
    #     2. The second step is to produce the product of all possible combinations between columns
    #     For example, if at the end of step 1, the table is :
    #     Col_1 | Col_2 | Col_3
    #     pat_1 | Pete  | Ginger
    #     pat_1 | P.    | Ginger
    #           | Peter | G.
    #
    #     The table resulting from step 2 will be :
    #     Col_1 | Col_2 | Col_3
    #     pat_1 | Pete  | Ginger
    #     pat_1 | Pete  | G.
    #     pat_1 | P.    | Ginger
    #     pat_1 | P.    | G.
    #     pat_1 | Peter | Ginger
    #     pat_1 | Peter | G.
    #
    #     Args:
    #         elements (fhir2dataset.Elements): instance of elements
    #
    #     Returns:
    #         pd.DataFrame: resulting dataframe
    #     """  # noqa
    #     cols_name = []
    #     dataset = []
    #
    #     for element in elements:
    #         MAPPING_CONCAT[element.concat_type](dataset, cols_name, element)
    #
    #     df = pd.DataFrame(list(product(*dataset)), columns=cols_name)
    #     return df

    def _init_data(self) -> pd.DataFrame:
        """generation of a dictionary whose keys correspond to the column name and the value to an empty list

        Returns:
            dict -- dictionary described above
        """  # noqa
        data = {}
        for element in self.elements.elements:
            if element.col_name not in data:  # Drop duplicates
                data[element.col_name] = []
        return pd.DataFrame(data)
