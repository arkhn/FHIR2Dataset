import re
from collections import defaultdict, OrderedDict


PREFIX = [" eq ", " ne ", " gt ", " lt ", " ge ", " le ", " sa ", " eb ", " ap "]


class FHIR2DatasetParser:
    def __init__(self):
        self.CLAUSES = OrderedDict()
        self.__split_mask_clauses = ""

        self.__init_clauses()
        self.__init_split_mask()
        self.__reset_config()

    def parse(self, SQL_string: str):
        self.__reset_config()
        SQL_string = SQL_string.replace("\n", " ")
        # print(f"SQL_string: {SQL_string}")

        items = re.split(self.__split_mask_clauses, SQL_string)
        items.remove("")
        for clause in self.CLAUSES.keys():
            for idx, item in enumerate(items):
                if item == clause:
                    # print(f"item: {item}")
                    self.CLAUSES[item](items[idx + 1])

        self.__create_config()
        return self.config

    def __create_config(self):
        self.config["from"] = dict(self.__from)
        self.config["select"] = dict(self.__select)
        self.config["where"] = dict(self.__where)
        if self.__inner_join:
            if not self.config["join"]:
                self.config["join"] = dict()
            self.config["join"]["inner"] = dict(self.__inner_join)
        if self.__child_join:
            if not self.config["join"]:
                self.config["join"] = dict()
            self.config["join"]["child"] = dict(self.__child_join)
        if self.__parent_join:
            if not self.config["join"]:
                self.config["join"] = dict()
            self.config["join"]["parent"] = dict(self.__parent_join)
        # print(f"self.config: {self.config}")

        keys_to_pop = []
        for key, value in self.config.items():
            if not value:
                keys_to_pop.append(key)
        # print(f"keys_to_pop: {keys_to_pop}")
        for key in keys_to_pop:
            self.config.pop(key)

    def __select_parser(self, string):
        item_parsed = re.split(self.__split_mask_select, string)
        # print("\nSELECT")
        # print(f"item_parsed: {item_parsed}")
        for item in item_parsed:
            alias, select_rule = re.split(r"\.", item, 1)
            assert alias in self.__from.keys()
            self.__select[alias].append(select_rule)
        # print(f"self.__select: {self.__select}")

    def __from_parser(self, string):
        item_parsed = re.split(self.__split_mask_from, string)
        # print("\nFROM")
        # print(f"item_parsed: {item_parsed}")
        if len(item_parsed) == 2:
            resource_type = item_parsed[0]
            alias = item_parsed[1]
            self.__from[alias] = resource_type
        elif len(item_parsed) == 1:
            resource_type = item_parsed[0]
            alias = item_parsed[0]
            self.__from[alias] = resource_type
        else:
            raise ValueError
        # print(f"self.__from: {self.__from}")

    def __inner_join_parser(self, string):
        alias_parent, searchparam_parent, alias_child = self.__join_parser(string)
        self.__inner_join[alias_parent][searchparam_parent] = alias_child

    def __child_join_parser(self, string):
        alias_parent, searchparam_parent, alias_child = self.__join_parser(string)
        self.__child_join[alias_parent][searchparam_parent] = alias_child

    def __parent_join_parser(self, string):
        alias_parent, searchparam_parent, alias_child = self.__join_parser(string)
        self.__parent_join[alias_parent][searchparam_parent] = alias_child

    def __join_parser(self, string):
        item_parsed = re.split(self.__split_mask_from_join, string)
        # print("\nJOIN")
        # print(f"item_parsed: {item_parsed}")
        assert len(item_parsed) == 2
        self.__from_parser(item_parsed[0])

        join_conditions = re.split(self.__split_mask_join, item_parsed[1])
        assert len(join_conditions) == 2

        alias_parent = None
        searchparam_parent = None
        alias_child = None
        for join_condition in join_conditions:
            alias, join_rule = re.split(r"\.", join_condition, 1)
            assert alias in self.__from.keys(), (
                f"The {alias} alias used in the {join_condition} join must have been referenced "
                "behind a FROM, INNER JOIN, PARENT JOIN or CHILD JOIN. "
                f"The only aliases referenced are here: {self.__from}"
            )
            if join_rule in ["id", "id ", " id", " id "]:
                if alias_child:
                    raise ValueError
                alias_child = alias
            else:
                if alias_parent or searchparam_parent:
                    raise ValueError
                alias_parent = alias
                searchparam_parent = join_rule

        return alias_parent, searchparam_parent, alias_child

    def __where_parser(self, string):
        item_parsed = re.split(self.__split_mask_where, string)
        # print("\nWHERE")
        # print(f"item_parsed: {item_parsed}")
        for where_condition in item_parsed:
            condition_parsed = re.split(self.__split_mask_where_condition, where_condition)
            assert len(condition_parsed) == 3
            alias, where_rule = re.split(r"\.", condition_parsed[0], 1)
            value = condition_parsed[2]
            if condition_parsed[1] in PREFIX:
                prefix = condition_parsed[1].replace(" ", "")
            else:
                prefix = "eq"
            self.__where[alias][where_rule] = {prefix: value}

    def __init_clauses(self):
        BASIC_CLAUSES = OrderedDict(
            {
                "FROM": self.__from_parser,
                "INNER JOIN": self.__inner_join_parser,
                "CHILD JOIN": self.__child_join_parser,
                "PARENT JOIN": self.__parent_join_parser,
                "SELECT": self.__select_parser,
                "WHERE": self.__where_parser,
            }
        )
        for clause, function in BASIC_CLAUSES.items():
            self.CLAUSES[f" {clause} "] = function
            self.CLAUSES[f"{clause} "] = function
            self.CLAUSES[f" {clause}"] = function
            self.CLAUSES[clause] = function

    def __init_split_mask(self):
        self.__split_mask_clauses = self.__create_mask_multiple_separators(self.CLAUSES.keys())
        self.__split_mask_from = " AS "
        self.__split_mask_select = " , |, "
        self.__split_mask_from_join = " ON "
        self.__split_mask_join = " = "
        self.__split_mask_where = " AND "
        self.__split_mask_where_condition = self.__create_mask_multiple_separators(PREFIX + [" = "])

    def __create_mask_multiple_separators(self, separators, keep_separators: bool = True):
        split_mask_multiple = ""
        for separator in separators:
            if split_mask_multiple:
                split_mask_multiple += f"|{separator}"
            else:
                split_mask_multiple += f"{separator}"
        if keep_separators:
            split_mask_multiple = f"({split_mask_multiple})"
        return split_mask_multiple

    def __reset_config(self):
        self.__select = defaultdict(list)
        self.__from = defaultdict(str)
        self.__inner_join = defaultdict(dict)
        self.__child_join = defaultdict(dict)
        self.__parent_join = defaultdict(dict)
        self.__where = defaultdict(dict)
        self.config = {
            "from": None,
            "join": None,
            "where": None,
            "select": None,
        }
