import re
from collections import defaultdict, OrderedDict
from collections.abc import Iterable

PREFIX = ["eq", "ne", "gt", "lt", "ge", "le", "sa", "eb", "ap"]


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

        _RE_COMBINE_WHITESPACE = re.compile(r"\s+")
        SQL_string = _RE_COMBINE_WHITESPACE.sub(" ", SQL_string).strip()

        items = re.split(self.__split_mask_clauses, SQL_string)

        if "" in items:
            items.remove("")
        for clause in self.CLAUSES.keys():
            for idx, item in enumerate(items):
                if item.upper() == clause:
                    self.CLAUSES[item.upper()](items[idx + 1])

        self.__create_config()
        return self.config

    def __create_config(self):
        self.config["from"] = dict(self.__from)
        self.config["select"] = dict(self.__select)
        self.config["where"] = dict(self.__where)
        self.config["join"]["inner"] = dict(self.__inner_join)
        self.config["join"]["child"] = dict(self.__child_join)
        self.config["join"]["parent"] = dict(self.__parent_join)

        self.config["join"] = {key: value for key, value in self.config["join"].items() if value}
        self.config = {key: value for key, value in self.config.items() if value}

    def __select_parser(self, string):
        item_parsed = re.split(self.__split_mask_select, string)
        for item in item_parsed:
            alias, select_rule = re.split(r"\.", item, 1)
            assert alias in self.__from.keys()
            self.__select[alias].append(select_rule)

    def __from_parser(self, string):
        item_parsed = re.split(self.__split_mask_from, string)
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
            if join_rule.strip() == "id":
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
        for where_condition in item_parsed:
            condition_parsed = re.split(self.__split_mask_where_condition, where_condition)
            assert len(condition_parsed) == 3
            alias, where_rule = re.split(r"\.", condition_parsed[0], 1)
            value = condition_parsed[2]
            if condition_parsed[1] in PREFIX:
                prefix = condition_parsed[1]
                self.__where[alias][where_rule] = {prefix: value}
            else:
                self.__where[alias][where_rule] = value

    def __init_clauses(self):
        self.CLAUSES = OrderedDict(
            {
                "FROM": self.__from_parser,
                "INNER JOIN": self.__inner_join_parser,
                "CHILD JOIN": self.__child_join_parser,
                "PARENT JOIN": self.__parent_join_parser,
                "SELECT": self.__select_parser,
                "WHERE": self.__where_parser,
            }
        )

    def __init_split_mask(self):
        self.__split_mask_clauses = self.__create_mask(
            self.CLAUSES.keys(), can_start_sentence=True, keep_separators=True
        )
        self.__split_mask_from = self.__create_mask("AS")
        self.__split_mask_select = self.__create_mask(",", optional_space_before=True)
        self.__split_mask_from_join = self.__create_mask("ON")
        self.__split_mask_join = self.__create_mask("=")
        self.__split_mask_where = self.__create_mask("AND")
        self.__split_mask_where_condition = self.__create_mask(PREFIX + ["="], keep_separators=True)

    def __create_mask(
        self,
        separators,
        keep_separators=False,
        case_insensitive: bool = True,
        can_start_sentence: bool = False,
        optional_space_before: bool = False,
        optional_space_after: bool = False,
    ):
        assert not (
            can_start_sentence and optional_space_before
        ), "Can't set to true both can_start_sentence and optional_space_before optional arguments"
        if isinstance(separators, str):
            mask = separators
        elif isinstance(separators, Iterable):
            mask = "|".join(separators)
        else:
            raise ValueError

        if keep_separators:
            mask = fr"({mask})"

        if can_start_sentence:
            mask = fr"(?:\s|^){mask}"
        elif optional_space_before:
            mask = fr"\s?{mask}"
        else:
            mask = fr"\s{mask}"

        if optional_space_after:
            mask = fr"{mask}\s?"
        else:
            mask = fr"{mask}\s"

        if case_insensitive:
            mask = fr"{mask}(?i)"

        return mask

    def __reset_config(self):
        self.__select = defaultdict(list)
        self.__from = defaultdict(str)
        self.__inner_join = defaultdict(dict)
        self.__child_join = defaultdict(dict)
        self.__parent_join = defaultdict(dict)
        self.__where = defaultdict(dict)
        self.config = {
            "from": None,
            "join": dict(),
            "where": None,
            "select": None,
        }
