import pandas as pd
import requests
import logging
from itertools import product

from fhir2dataset.timer import timing
from fhir2dataset.fhirpath import multiple_search_dict

logger = logging.getLogger(__name__)


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
    """  # noqa

    @timing
    def __init__(
        self,
        url: str,
        elements: dict,
        elements_concat_type: dict,
        main_resource_alias: str,
        token: str = None,
    ):
        CallApi.__init__(self, url, token)
        self.main_resource_alias = main_resource_alias
        self.elements = elements
        self.elements_concat_type = elements_concat_type
        self.searchparam_fhirpath = self._get_dict_searchparam_fhirpath()
        self.data = self._init_data()

    @timing
    def dict_to_dataframe(self) -> pd.DataFrame:
        """transforms the collected data into a dataframe

        Returns:
            pd.DataFrame -- collected data into a dataframe
        """
        df = pd.DataFrame(self.data)
        logger.debug(f"{self.main_resource_alias} dataframe builded head - \n{df.to_string()}")
        return df

    @timing
    def _concatenate(self, column):
        result = []
        for list_cell in column:
            if isinstance(list_cell, list):
                result.extend([value for value in list_cell])
            else:
                result.append(list_cell)
        return result

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
        data = pd.DataFrame(self.data)
        for json_resource in self.results:
            lines = self._get_match_search(json_resource)
            df = self._flatten_item_results(lines)
            data = pd.concat([data, df])
        self.data = data

    @timing
    def _flatten_item_results(self, lines):
        infos = self.elements_concat_type
        cols = list(lines.keys())
        final_cols = []

        originDataset = []
        for col in cols:
            if infos[col] == "cell":
                originDataset.append([lines[col]])
                final_cols.append(col)
            elif infos[col] == "col":
                for i in range(len(lines[col])):
                    originDataset.append([lines[col][i]])
                    final_cols.append(f"{col}_{i}")
            else:
                originDataset.append(lines[col])
                final_cols.append(col)

        df2 = pd.DataFrame(list(product(*originDataset)), columns=final_cols)
        return df2

    @timing
    def _get_match_search(self, json_resource) -> dict:
        lines = self._init_data()
        item = multiple_search_dict(
            [json_resource["resource"]], list(self.searchparam_fhirpath.values())
        )
        for idx, fhirpath in enumerate(self.searchparam_fhirpath.keys()):
            lines[fhirpath].extend(item[0][idx])
        return lines

    def _init_data(self) -> dict:
        """generation of a dictionary whose keys correspond to the column name and the value to an empty list

        Returns:
            dict -- dictionary described above
        """  # noqa
        data = dict()
        for searchparam_or_fhirpath in self.searchparam_fhirpath.keys():
            data[searchparam_or_fhirpath] = []
        return data

    def _get_dict_searchparam_fhirpath(self):
        """transforms the element to be retrieved at the resource level (in elements attribute) in the json file into the corresponding fhirpath expression. The result is stored in expression attribute
        
        Returns:
            dict -- dictionary described above
        """  # noqa
        dict_searchparam_fhirpath = dict()
        for dico in self.elements.values():
            for searchparam_or_fhirpath, fhirpath in dico.items():
                if searchparam_or_fhirpath in dict_searchparam_fhirpath:
                    assert (
                        dict_searchparam_fhirpath[searchparam_or_fhirpath] == fhirpath
                    ), f"There's a conflict between two fhirpaths: {dict_searchparam_fhirpath[searchparam_or_fhirpath]} and {fhirpath}"
                else:
                    dict_searchparam_fhirpath[searchparam_or_fhirpath] = fhirpath
        return dict_searchparam_fhirpath
