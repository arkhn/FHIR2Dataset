import json
import requests
import networkx as nx


class Query:
    def __init__(
        self,
        service_base_url: str,
        capabilitystatement_path: str = None,
    ) -> None:
        self.base = service_base_url
        self.possible_references = self._get_rev_include_possibilities(
            capabilitystatement_path
        )
        """Instantiate the class and create the query object

        Arguments:
            service_base_url {str} -- the Service Base URL
            capabilitystatement_path {str} -- path to the json file that
            contains a resource of type CapabilityStatement
        """

        # to represent the relationships (references) between resources
        self.rscs_graph = nx.DiGraph()
        self.rscs_type = dict()

        self.main_internal_name = None
        self.url_params = ""
        self.url_rev_include = ""
        self.count = None
        self.api_url = None

    def execute(
        self,
        select_dict: dict,
        from_dict: dict,
        join_dict: dict = None,
        where_dict: dict = None,
    ):
        """Executes the query and returns (not defined yet?)

        Arguments:
            select_dict {dict} -- dictionary containing the attributes 
            to be selected from the different resources
            from_dict {dict} -- dictionary containing all requested 
            resources

        Keyword Arguments:
            join_dict {dict} -- dictionary containing the inner join 
            rules between resources (default: {None})
            where_dict {dict} -- dictionary containing the (cumulative) 
            conditions to be met by the resources (default: {None})
        """
        self._from(**from_dict)
        if join_dict:
            self._join(**join_dict)
        if where_dict:
            self._where(**where_dict)
        self._select(**select_dict)

        self.api_url = self._compute_url()

        # to do :
        # 1. retrieve the result of the request
        # 2. Do all post-treatments

    def from_config(self, config: dict):
        """executes the query from a dictionary in the format of a 
        configuration file

        Arguments:
            config {dict} -- dictionary in the format of a configuration
            file
        """
        rename_keys = [
            ("from", "from_dict"),
            ("where", "where_dict"),
            ("select", "select_dict"),
            ("join", "join_dict"),
        ]
        for old_key, new_key in rename_keys:
            try:
                config[new_key] = config.pop(old_key)
            except:
                pass
        self.execute(**config)

    def _compute_url(self) -> str:
        """Generates the API request url satisfying the conditions from,
        join, where and select

        Returns:
            str -- corresponding API request url
        """
        # to do verify self.base finish by '/'
        api_url = (
            self.base + self.rscs_type[self.main_internal_name] + "?"
        )
        if self.url_params and self.url_rev_include:
            api_url_bis = api_url + (
                self.url_params
                + "&"
                + self.url_rev_include
                + "&_format=json"
            )
            api_url = f"{api_url}{self.url_params}&{self.url_rev_include}&_format=json"
            assert api_url == api_url_bis, "fstring doesn't work"
        else:
            api_url_bis = api_url + (
                self.url_params + self.url_rev_include + "&_format=json"
            )
            api_url = f"{api_url}{self.url_params}{self.url_rev_include}&_format=json"
            assert api_url == api_url_bis, "fstring doesn't work"
        return api_url

    def _from(self, **ressourcetype_internalname: dict):
        """Registers the resources concerned by the query
        """
        for (
            ressource_type,
            internal_name,
        ) in ressourcetype_internalname.items():
            self.rscs_graph.add_node(internal_name)
            self.rscs_type[internal_name] = ressource_type

    def _join(self, **join_as):
        """Builds the links between the resources involved in the query
        """
        for parent_rsc_internal, child_dict in join_as.items():
            parent_rsc_type = self.rscs_type[parent_rsc_internal]
            for parent_rsc_attribute in child_dict.keys():
                child_rsc_type = self.rscs_type[
                    child_dict[parent_rsc_attribute]
                ]
                check = parent_rsc_type + "." + parent_rsc_attribute
                if (
                    check
                    in self.possible_references[parent_rsc_type][
                        "searchInclude"
                    ]
                ):
                    attribute_child = (
                        parent_rsc_attribute
                        + ":"
                        + child_rsc_type
                        + "."
                    )
                    include_url = (
                        parent_rsc_type
                        + ":"
                        + parent_rsc_attribute
                        + ":"
                        + child_rsc_type
                    )

                    self.rscs_graph.add_edge(
                        parent_rsc_internal,
                        child_dict[parent_rsc_attribute],
                        attribute_child=attribute_child,
                        include=include_url,
                    )
                if (
                    check
                    in self.possible_references[child_rsc_type][
                        "searchRevInclude"
                    ]
                ):
                    attribute_parent = (
                        parent_rsc_type
                        + ":"
                        + parent_rsc_attribute
                        + ":"
                    )
                    revinclud_url = (
                        parent_rsc_type
                        + ":"
                        + parent_rsc_attribute
                        + ":"
                        + child_rsc_type
                    )

                    self.rscs_graph.add_edge(
                        child_dict[parent_rsc_attribute],
                        parent_rsc_internal,
                        attribute_parent=attribute_parent,
                        revinclude=revinclud_url,
                    )
                else:
                    possibilities = self.possible_references[
                        parent_rsc_type
                    ]["searchInclude"]
                    print(f"{check} not in {possibilities}")

    def _where(self, **wheres):
        """Builds the url_params that best respects the cumulative 
        conditions specified on resource attributes
        """
        # With the current approach, adjustments must be made to remove 
        # results that do not match the conditions (due to the fact that
        # parameters chained to _has parameters are not cumulative).
        max_conditions = -1
        for internal_name in wheres.keys():
            # the main resource chosen is the one with the most
            # specified parameters. Choice to be discussed, here I think
            # that it allows to make the best possible selection
            # knowing that in the chained parameters and with _has are
            # not cumulative.
            curr_num_conditions = len(wheres[internal_name].keys())
            if curr_num_conditions > max_conditions:
                max_conditions = curr_num_conditions
                self.main_internal_name = internal_name

        for internal_name, conditions in wheres.items():
            url_temp = ""
            to_rsc = ""

            # Construction of the path from the main resource to the
            # resource on which the parameter(s) will be applied
            if internal_name != self.main_internal_name:
                internal_path = nx.shortest_path(
                    self.rscs_graph,
                    source=self.main_internal_name,
                    target=internal_name,
                )
                for ind in range(len(internal_path) - 1):
                    edge = self.rscs_graph.edges[
                        internal_path[ind], internal_path[ind + 1]
                    ]
                    if "attribute_child" in edge:
                        to_rsc = edge["attribute_child"]
                    elif "attribute_parent" in edge:
                        to_rsc = "_has:" + edge["attribute_parent"]

            for search_param, value_full in conditions.items():
                # add assert search_param in CapabilityStatement
                value = ""

                # handles the case where a prefix has been specified
                # value_full={"ge": "1970"}
                if type(value_full) is dict:
                    for k, v in value_full.items():
                        value += k + v
                else:
                    value = value_full

                if url_temp != "":
                    url_temp += (
                        "&" + to_rsc + search_param + "=" + value
                    )
                else:
                    url_temp += to_rsc + search_param + "=" + value

            if self.url_params:
                self.url_params += "&" + url_temp
            else:
                self.url_params = url_temp

    def _select(self, **selects):
        """constructs the include url that allows to retrieve 
        information from resources neighboring the main resource when 
        its attributes are requested in the select
        """
        resources_to_add = list(selects.keys())

        # handles the case of count
        if "count" in selects.keys():
            self.count = selects["count"]
            resources_to_add += selects["count"]
            resources_to_add.remove("count")

        resources_to_add = set(resources_to_add)

        if not self.main_internal_name:
            # if there was no where condition, default selection of the
            # main resource
            self.main_internal_name = resources_to_add[0]

        # loop to include information about resources other than the
        # main resource
        for internal_name in resources_to_add:
            if internal_name != self.main_internal_name:
                url_temp = ""
                internal_path = nx.shortest_path(
                    self.rscs_graph,
                    source=self.main_internal_name,
                    target=internal_name,
                )
                for ind in range(len(internal_path) - 1):
                    edge = self.rscs_graph.edges[
                        internal_path[ind], internal_path[ind + 1]
                    ]
                    if "include" in edge:
                        if url_temp:
                            url_temp += (
                                "&"
                                + "_include:iterate="
                                + edge["include"]
                            )
                        else:
                            url_temp = "_include=" + edge["include"]
                    elif "revinclude" in edge:
                        if url_temp:
                            url_temp += (
                                "&"
                                + "_revinclude:iterate="
                                + edge["revinclude"]
                            )
                        else:
                            url_temp = (
                                "_revinclude=" + edge["revinclude"]
                            )
                if self.url_rev_include:
                    self.url_rev_include += "&" + url_temp
                else:
                    self.url_rev_include += url_temp

    def _get_rev_include_possibilities(
        self, capabilitystatement_path: str = None
    ):
        """Builds a dictionary that will indicate for each type of 
        resource which are its mother resources (revinclude) and its 
        daughter resources (include).

        Arguments:
            capabilitystatement_path {str} -- path to the json file that
            contains a resource of type CapabilityStatement
        """
        if capabilitystatement_path:
            capabilitystatement = self._get_capabilitystatement_from_file(
                capabilitystatement_path
            )
        else:
            capabilitystatement = (
                self._get_capabilitystatement_from_api()
            )

        dict_reference = dict()
        for ressource in capabilitystatement["resource"]["rest"][0][
            "resource"
        ]:  # check the 0 , we could have several
            type = ressource["type"]
            dict_reference[type] = dict()
            try:
                dict_reference[type]["searchRevInclude"] = ressource[
                    "searchRevInclude"
                ]
            except:
                pass
            try:
                dict_reference[type]["searchInclude"] = ressource[
                    "searchInclude"
                ]
            except:
                pass
        return dict_reference

    def _get_capabilitystatement_from_file(
        self, capabilitystatement_path: str
    ) -> dict:
        """Get the CapabilityStatement from the json file

        Arguments:
            capabilitystatement_path {str} -- path to the json file that
             contains a resource of type CapabilityStatement
        Returns:
            dict -- dict object containing a CapabilityStatement 
            resource
        """
        with open(capabilitystatement_path) as json_file:
            capabilitystatement = json.load(json_file)
        return capabilitystatement

    def _get_capabilitystatement_from_api(self) -> dict:
        """Get the CapabilityStatement from the base

        Returns:
            dict --  dict object containing a CapabilityStatement 
            resource
        """
        url = self.base + "/" + "CapabilityStatement?"
        response = requests.get(url)
        # 0 by default but we must investigate how to chose the right
        # CapabilityStatement ?
        capabilitystatement = response.json()["entry"][0]
        return capabilitystatement

    def draw_relations(self):
        """draws the possible relationships between the requested 
        resources
        """
        import matplotlib.pyplot as plt

        layout = nx.random_layout(self.rscs_graph)
        nx.draw_networkx(self.rscs_graph, pos=layout)
        nx.draw_networkx_labels(self.rscs_graph, pos=layout)
        nx.draw_networkx_edge_labels(self.rscs_graph, pos=layout)
        plt.show()