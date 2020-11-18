import pandas as pd
import logging
import tqdm

from fhir2dataset.graphquery import GraphQuery
from fhir2dataset.fhirrules_getter import FHIRRules
from fhir2dataset.api_caller import ApiGetter
from fhir2dataset.url_builder import URLBuilder
from fhir2dataset.graph_tools import join_path

logger = logging.getLogger(__name__)


class Query:
    """Query Executor

    Description:
        This module purpose is to perform SQL-type queries whose information is
        filled in configuration files of the form:
        ```
        {
            "from": {
                "alias n°1": "Resource type 1",
                "alias n°2": "Resource type 2",
                "alias n°3": "Resource type 3",
                ...
            },
            "select": {
                "alias n°1": [
                    "searchparam/fhirpath of attribute a of resource type 1",
                    "searchparam/fhirpath of attribute b of resource type 1",
                    "searchparam/fhirpath of attribute c of resource type 1"
                ],
                "alias n°2": [
                    "searchparam of attribute a of resource type 2",
                    ...
                ],
                ...
            },
            "join": {
                "inner": {
                    "alias n°1": {
                        "searchparam of attribute d, which is of type Reference, of resource type 1": "alias n°2"
                    },
                    ...
                },
                "child": {
                    "alias n°2": {
                        "searchparam of attribute b, which is of type Reference, of resource type 2": "alias n°3"
                    },
                    ...
                },
                "parent": {
                    ...
                }
            },
            "where": {
                "alias n°2": {
                    "searchparam of attribute c of resource type 2": "value 1",
                    "searchparam of attribute d of resource type 2": "value 2"
                },
                "alias n°3": {
                    "searchparam of attribute a of resource type 2": "value 3",
                    "searchparam of attribute b of resource type 2": "value 4"
                },
                ...
            }
        }
        ```
        for the next associated SQL query:
        ```
        SELECT (alias n°1).a, (alias n°1).b, (alias n°1).c, (alias n°2).a FROM (Resource type 1) as (alias n°1)
        INNER JOIN (Resource type 2) as (alias n°2)
        ON (alias n°1).d = (alias n°2)
        INNER JOIN (Resource type 3) as (alias n°3)
        ON (alias n°2).b = (alias n°3) WHERE (alias n°2).c = "value 1"
        AND (alias n°2).d = "value 2"
        AND (alias n°3).a = "value 3"
        AND (alias n°3).b = "value 4"
    ```

    Attributes:
        config {dict} -- dictionary storing the initial request
        graph_query {type(GraphQuery)} -- instance of a GraphQuery object that gives a graphical representation of the query
        dataframes {dict} -- dictionary storing for each alias the resources requested on the api in tabular format
        main_dataframe {DataFrame} -- pandas dataframe storing the final result table

    Example:
        import fhir2dataset
        import logging

        logging.basicConfig(level=logging.INFO)
        query = Query(fhir_api_url=fhir_api_url, fhir_rules=fhir_rules, token=token)
        query.from_config(config)
        query.execute()
        df = query.main_dataframe
    """  # noqa

    def __init__(
        self,
        fhir_api_url: str = None,
        fhir_rules: type(FHIRRules) = None,
        token: str = None,
    ):
        """Requestor's initialisation

        Arguments:
            fhir_api_url {str} -- The Service Base URL (e.g. http://hapi.fhir.org/baseR4/)

        Keyword Arguments:
            fhir_rules {type(FHIRRules)} -- an instance of a FHIRRules-type object. If the instance is not filled a default version will be used. (default: {None})
            token {str} -- bearer token authentication if necessary (default: {None})
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
            config {dict} -- dictionary in the format of a configuration file
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

        Keyword Arguments::
            debug {bool} -- if debug is true then the columns needed for internal processing are kept in the final dataframe. Otherwise only the columns of the select are kept in the final dataframe. (default: {False})
        """  # noqa
        self.graph_query = GraphQuery(fhir_api_url=self.fhir_api_url, fhir_rules=self.fhir_rules)
        self.graph_query.execute(**self.config)
        with tqdm.tqdm(total=1000) as pbar:
            time_frac = round(1000 / len(self.graph_query.resources_alias_info))
            for resource_alias in self.graph_query.resources_alias_info.keys():
                resource_alias_info = self.graph_query.resources_alias_info[resource_alias]
                elements = resource_alias_info.elements
                url_builder = URLBuilder(
                    fhir_api_url=self.fhir_api_url,
                    graph_query=self.graph_query,
                    main_resource_alias=resource_alias,
                )
                url = url_builder.compute()
                call = ApiGetter(
                    url=url, elements=elements, token=self.token, pbar=pbar, time_frac=time_frac
                )
                call.get_all()
                self.dataframes[resource_alias] = call.df
        self._clean_columns()
        for resource_alias, dataframe in self.dataframes.items():
            logger.debug(f"{resource_alias} dataframe builded head - \n{dataframe.to_string()}")
        # We check if there is more than 1 alias of resource
        if len(self.dataframes) > 1:
            self.main_dataframe = self._join()
        else:
            self.main_dataframe = list(self.dataframes.values())[0]

        logger.debug(
            f"Main dataframe builded head before columns selection-"
            f"\n{self.main_dataframe.to_string()}"
        )
        if not debug:
            self._select_columns()
            self._remove_lists()

    def _select_columns(self):
        """Clean the final dataframe to keep only the columns of the select"""
        final_columns = []
        for resource_alias, resource_alias_info in self.graph_query.resources_alias_info.items():
            for element in resource_alias_info.elements.get_subset_elements(goal="select"):
                final_columns.append(f"{resource_alias}:{element.col_name}")
        self.main_dataframe = self.main_dataframe[final_columns]

    def _remove_lists(self):
        """Remove lists from columns with only single elements"""
        if len(self.main_dataframe) > 0:
            df = self.main_dataframe.copy()
            for column in df.columns:
                lengths = df[column].str.len()
                try:
                    if all(len < 2 for len in lengths):
                        df[column] = df[column].apply(lambda x: x[0] if isinstance(x, list) else x)
                        logger.info(
                            f"extraction of the unique element from the lists composing "
                            f"the {column} column"
                        )
                except Exception:
                    pass
            self.main_dataframe = df

    def _join(self) -> pd.DataFrame:
        """Execute the joins one after the other in the order specified by the
        join_path function.

        Returns:
            pd.DataFrame -- dataframe containing all joined resources
        """
        list_join = join_path(self.graph_query.resources_alias_graph)
        main_alias_join = list_join[0][0]
        main_df = self.dataframes[main_alias_join]
        for alias_1, alias_2 in list_join:
            df_1 = main_df
            df_2 = self.dataframes[alias_2]
            main_df = self._join_2_df(alias_1, alias_2, df_1, df_2)
        return main_df

    def _group_lines(self, df, col_name):
        logger.debug(f"dataframe before being grouped \n{df.to_string()}")
        if not df.empty:
            cols_group = [col_name]
            if cols_group:
                cols = df.columns.to_list()
                cols_list = [col_name for col_name in cols if col_name not in cols_group]
                dict_cols_list = {col: self._concatenate for col in cols_list}
                df = df.groupby(cols_group).agg(dict_cols_list)
                df.reset_index(inplace=True)
            logger.debug(f"dataframe after being grouped on {cols_group}:\n{df.to_string()}")
        return df

    def _concatenate(self, column):
        result = []
        for list_cell in column:
            if isinstance(list_cell, list):
                result.extend(list_cell)
            else:
                result.append(list_cell)
        return result

    def _join_2_df(
        self, alias_1: str, alias_2: str, df_1: pd.DataFrame, df_2: pd.DataFrame
    ) -> pd.DataFrame:
        """Executes the join between two dataframes

        The join key is the id of the child resource.
        This id is contained in :
            * in the column child_alias:id of the child resource table named child_alias (e.g. parent:id for a parent dataframe)
            * in the alias_parent:searchparam_parent column of the parent resource table named alias_parent (e.g. condition:subject.reference for a condition dataframe)

        The function is in charge of finding out who is the mother resource and who is the daughter resource.

        Arguments:
            alias_1 {str} -- df_1 alias
            alias_2 {str} -- df_2 alias
            df_1 {pd.DataFrame} -- dataframe containing the elements of a resource
            df_2 {pd.DataFrame} -- dataframe containing the elements of a resource
        Returns:
            pd.DataFrame -- dataframe containing the elements of the 2 resources according to an inner join
        """  # noqa
        edge_info = self.graph_query.resources_alias_graph.edges[alias_1, alias_2]["info"]
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
        elif how != "inner":
            how = "inner"

        if alias_1 == alias_parent:
            df_merged_inner = pd.merge(
                left=df_1, right=df_2, left_on=parent_on, right_on=child_on, how=how
            )
        else:
            df_merged_inner = pd.merge(
                left=df_2, right=df_1, left_on=parent_on, right_on=child_on, how=how
            )
        return df_merged_inner

    def _clean_columns(self):
        """performs preprocessing on all dataframes harvested in the dataframe attribute:
        * adds the resource type in front of an element id so that the resource id matches the references of its parent resource references
        * adds the table alias as a prefix to each column name
        """  # noqa
        for resource_alias, df in self.dataframes.items():
            resource_type = self.graph_query.resources_alias_info[resource_alias].resource_type

            df = df.pipe(_add_resource_type_to_id, resource_type=resource_type)

            self.dataframes[resource_alias] = df.add_prefix(f"{resource_alias}:")


def _add_resource_type_to_id(df, resource_type: str):
    # add assert to check that there is only one id in list
    df["from_id"] = f"{resource_type}/" + df["from_id"]
    return df
