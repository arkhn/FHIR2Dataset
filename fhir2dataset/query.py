import logging

import pandas as pd
import tqdm

from fhir2dataset.api import ApiRequest
from fhir2dataset.fhirrules import FHIRRules
from fhir2dataset.graphquery import GraphQuery
from fhir2dataset.tools.graph import join_path
from fhir2dataset.url_builder import URLBuilder

logger = logging.getLogger(__name__)


class Query:
    """Query Executor

    Description:
        This module purpose is to perform SQL-type queries whose information is
        filled in configuration files of the form:
        ```
        {
            "from": {
                "alias_1": "Resource type 1",
                "alias_2": "Resource type 2",
                "alias_3": "Resource type 3",
                ...
            },
            "select": {
                "alias_1": [
                    "searchparam/fhirpath of attribute a of resource type 1",
                    "searchparam/fhirpath of attribute b of resource type 1",
                    "searchparam/fhirpath of attribute c of resource type 1"
                ],
                "alias_2": [
                    "searchparam of attribute a of resource type 2",
                    ...
                ],
                ...
            },
            "join": {
                "inner": {
                    "alias_1": {
                        "searchparam of attribute d, which is of type Reference, of resource type 1": "alias_2"
                    },
                    ...
                },
                "inner": {
                    "alias_2": {
                        "searchparam of attribute b, which is of type Reference, of resource type 2": "alias_3"
                    },
                    ...
                }
            },
            "where": {
                "alias_2": {
                    "searchparam of attribute c of resource type 2": "value 1",
                    "searchparam of attribute d of resource type 2": "value 2"
                },
                "alias_3": {
                    "searchparam of attribute a of resource type 2": "value 3",
                    "searchparam of attribute b of resource type 2": "value 4"
                },
                ...
            }
        }
        ```
        for the next associated SQL query:
        ```
        SELECT alias_1.a, alias_1.b, alias_1.c, alias_2.a FROM (Resource type 1) as alias_1
        INNER JOIN (Resource type 2) as alias_2
        ON alias_1.d = alias_2.id
        INNER JOIN (Resource type 3) as alias_3
        ON alias_2.b = alias_3.id
        WHERE alias_2.c = "value 1"
        AND alias_2.d = "value 2"
        AND alias_3.a = "value 3"
        AND alias_3.b = "value 4"
        ```

    Attributes:
        config (dict): dictionary storing the initial request
        graph_query (GraphQuery): instance of a GraphQuery object that gives a graphical
            representation of the query
        dataframes (dict): dictionary storing for each alias the resources requested on
            the api in tabular format
        main_dataframe (DataFrame): pandas dataframe storing the final result table
    """  # noqa

    def __init__(
        self,
        fhir_api_url: str = None,
        token: str = None,
        fhir_rules: FHIRRules = None,
    ):
        """Requestor's initialisation

        Arguments:
            fhir_api_url (str): the service base URL (e.g. http://hapi.fhir.org/baseR4/)
            token (str): (Optional) the bearer token to authenticate to the FHIR server,
                if necessary
            fhir_rules (FHIRRules): (Optional) an instance of FHIR rules, initialized
                with search parameters
        """  # noqa
        self.fhir_api_url = fhir_api_url or "http://hapi.fhir.org/baseR4/"
        if not fhir_rules:
            fhir_rules = FHIRRules(fhir_api_url=self.fhir_api_url)
        self.fhir_rules = fhir_rules
        self.token = token

        self.config = None
        self.graph_query = None
        self.dataframes = {}
        self.main_dataframe = None

    def from_config(self, config: dict):
        """Executes the query from a dictionary in the format of a configuration file

        Arguments:
            config (dict): dictionary in the format of a configuration file
        """
        self.config = {
            "from_dict": config.get("from", None),
            "select_dict": config.get("select", None),
            "where_dict": config.get("where", None),
            "join_dict": config.get("join", None),
        }
        return self

    def execute(self, debug: bool = False):
        """Executes the complete query

        1. constructs a GraphQuery object to store the query as a graph
        2. builds the url of the requests to send to the API
        3. retrieves the answers from the api and puts them as tables in the dataframes attribute
        4. executes joins to return the result table in the main_dataframe attribute

        Arguments:
            debug (bool): if debug is true then the columns needed for internal processing
                are kept in the final dataframe. Otherwise only the columns of the select are
                kept in the final dataframe. (default: {False})
        """  # noqa
        self.graph_query = GraphQuery(fhir_api_url=self.fhir_api_url, fhir_rules=self.fhir_rules)
        self.graph_query.build(**self.config)

        with tqdm.tqdm(
            total=1, unit_scale=100, bar_format="{l_bar}{bar}| {n:.02f}/{total:.02f}"
        ) as pbar:
            bar_frac = 1 / len(self.graph_query.resources_by_alias)
            for resource_alias, resource in self.graph_query.resources_by_alias.items():
                url = URLBuilder(
                    fhir_api_url=self.fhir_api_url,
                    graph_query=self.graph_query,
                    main_resource_alias=resource_alias,
                ).compute()
                call = ApiRequest(
                    url=url,
                    elements=resource.elements,
                    token=self.token,
                    pbar=pbar,
                    bar_frac=bar_frac,
                )
                self.dataframes[resource_alias] = call.get_all()

        self._clean_columns()

        for resource_alias, dataframe in self.dataframes.items():
            logger.debug(f"{resource_alias} dataframe builded head - \n{dataframe.to_string()}")

        # We check if there is more than 1 alias of resource
        if len(self.dataframes) > 1:
            self.main_dataframe = self._join()
        else:
            self.main_dataframe = list(self.dataframes.values())[0]

        self.main_dataframe = self.main_dataframe.reset_index(drop=True)

        logger.debug(
            f"Main dataframe builded head before columns selection-"
            f"\n{self.main_dataframe.to_string()}"
        )
        if not debug:
            self.__select_columns()
            self.__remove_lists()

        return self.main_dataframe

    def _join(self) -> pd.DataFrame:
        """Execute the joins one after the other in the order specified by the
        join_path function.

        Returns:
            pd.DataFrame: dataframe containing all joined resources
        """
        list_join = join_path(self.graph_query.resources_graph)
        main_alias_join = list_join[0][0]
        main_df = self.dataframes[main_alias_join]
        for alias_1, alias_2 in list_join:
            df_1 = main_df
            df_2 = self.dataframes[alias_2]
            main_df = self._join_2_df(alias_1, alias_2, df_1, df_2)
        return main_df

    def _join_2_df(
        self, alias_1: str, alias_2: str, df_1: pd.DataFrame, df_2: pd.DataFrame
    ) -> pd.DataFrame:
        """Executes the join between two dataframes

        The join key is the id of the child resource.
        This id is contained in :
            * in the column child_alias:id of the child resource table named child_alias
              (e.g. parent:id for a parent dataframe)
            * in the alias_parent:searchparam_parent column of the parent resource table
               named alias_parent (e.g. condition:subject.reference for a condition dataframe)

        The function is in charge of finding out who is the mother resource and who is the
        daughter resource.

        Arguments:
            alias_1 (str): df_1 alias
            alias_2 (str): df_2 alias
            df_1 (pd.DataFrame): dataframe containing the elements of a resource
            df_2 (pd.DataFrame): dataframe containing the elements of a resource
        Returns:
            pd.DataFrame: dataframe containing the elements of the 2 resources according to
                an inner join
        """  # noqa
        edge_info = self.graph_query.resources_graph.edges[alias_1, alias_2]["info"]
        alias_parent = edge_info.parent
        alias_child = edge_info.child

        how = edge_info.join_how
        searchparam_parent = edge_info.searchparam_parent

        parent_on = f"{alias_parent}:join_{searchparam_parent}"
        child_on = f"{alias_child}:from_id"

        if how == "child":
            how = "right"
        elif how == "parent":
            how = "left"
        else:
            how = "inner"

        if alias_1 == alias_parent:
            df_1 = df_1.explode(parent_on)
            df_2 = df_2.explode(child_on)
            df_merged_inner = pd.merge(
                left=df_1, right=df_2, left_on=parent_on, right_on=child_on, how=how
            )
        else:
            df_1 = df_1.explode(child_on)
            df_2 = df_2.explode(parent_on)
            df_merged_inner = pd.merge(
                left=df_2, right=df_1, left_on=parent_on, right_on=child_on, how=how
            )
        return df_merged_inner

    def _clean_columns(self):
        """Perform preprocessing on all dataframes harvested in the dataframe attribute:
        - Add the resource type in front of an element id so that the resource id matches
          the references of its parent resource references
        - Add the table alias as a prefix to each column name
        """  # noqa

        def _add_resource_type_to_id(df, resource_type: str):
            # add assert to check that there is only one id in list
            df["from_id"] = f"{resource_type}/" + df["from_id"]
            return df

        for resource_alias, df in self.dataframes.items():
            resource_type = self.graph_query.resources_by_alias[resource_alias].resource_type

            df = df.pipe(_add_resource_type_to_id, resource_type=resource_type)

            self.dataframes[resource_alias] = df.add_prefix(f"{resource_alias}:")

    def __select_columns(self):
        """Clean the final dataframe to keep only the columns of the select"""
        final_columns = []
        for resource_alias, resource in self.graph_query.resources_by_alias.items():
            for element in resource.elements.where(goal="select"):
                final_columns.append(f"{resource_alias}:{element.col_name}")
        self.main_dataframe = self.main_dataframe[final_columns]

    def __remove_lists(self):
        """Remove lists from columns with only single elements"""

        def unlist(x):
            """Auxiliary function to squeeze lists with one element"""
            if isinstance(x, list) and len(x) == 1:
                return unlist(x[0])
            else:
                return x

        if len(self.main_dataframe) > 0:
            df = self.main_dataframe.copy()
            for column in df.columns:
                df[column] = df[column].apply(unlist)
            self.main_dataframe = df
