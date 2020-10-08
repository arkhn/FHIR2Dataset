import re
from collections import defaultdict
from collections.abc import Iterable

from typing import List

PREFIX = ["eq", "ne", "gt", "lt", "ge", "le", "sa", "eb", "ap"]


def create_mask(
    separators,
    keep_separators=False,
    case_insensitive: bool = True,
    can_start_sentence: bool = False,
    optional_space_before: bool = False,
    optional_space_after: bool = False,
    optional_spaces: bool = None,
):
    if optional_spaces is not None:
        optional_space_before = optional_spaces
        optional_space_after = optional_spaces

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


class Parser:
    def __init__(self):
        self.CLAUSES = {
            "FROM": self.__from_parser,
            "INNER JOIN": self.__inner_join_parser,
            "CHILD JOIN": self.__child_join_parser,
            "PARENT JOIN": self.__parent_join_parser,
            "SELECT": self.__select_parser,
            "WHERE": self.__where_parser,
            "ORDER BY": self.__order_by_parser,
            "GROUP BY": self.__group_by_parser,
            "UNION": self.__union_parser,
            "LIMIT": self.__limit_parser,
        }

        self.__select = defaultdict(list)
        self.__from = defaultdict(str)
        self.__inner_join = defaultdict(dict)
        self.__child_join = defaultdict(dict)
        self.__parent_join = defaultdict(dict)
        self.__where = defaultdict(dict)

    def from_sql(self, sql_string: str) -> dict:
        items = self.__split_sql_string(sql_string)
        for clause in self.CLAUSES.keys():
            for idx, item in enumerate(items):
                if item.upper() == clause:
                    self.CLAUSES[item.upper()](items[idx + 1])
        return self.__to_dict()

    def __split_sql_string(self, sql_string: str) -> List[str]:
        sql_string = sql_string.replace("\n", " ")
        _RE_COMBINE_WHITESPACE = re.compile(r"\s+")  # noqa
        sql_string = _RE_COMBINE_WHITESPACE.sub(" ", sql_string).strip()
        split_mask_clauses = create_mask(
            self.CLAUSES.keys(), can_start_sentence=True, keep_separators=True
        )
        return re.split(split_mask_clauses, sql_string)

    def __to_dict(self) -> dict:
        config = {
            "from": dict(self.__from),
            "select": dict(self.__select),
            "where": dict(self.__where),
            "join": {
                "inner": dict(self.__inner_join),
                "child": dict(self.__child_join),
                "parent": dict(self.__parent_join),
            },
        }
        config["join"] = {key: value for key, value in config["join"].items() if value}
        return {key: value for key, value in config.items() if value}

    def __select_parser(self, string):
        item_parsed = re.split(create_mask(",", optional_spaces=True), string)
        for item in item_parsed:
            alias, select_rule = re.split(r"\.", item, 1)
            assert (
                alias in self.__from.keys()
            ), f"Ressource {alias} was used in SELECT {item} but was not defined"
            self.__select[alias].append(f"{self.__from[alias]}.{select_rule}")

    def __from_parser(self, string):
        item_parsed = re.split(create_mask("AS"), string)
        if len(item_parsed) == 2:
            resource_type = item_parsed[0]
            alias = item_parsed[1]
            self.__from[alias] = resource_type
        elif len(item_parsed) == 1:
            resource_type = item_parsed[0]
            alias = item_parsed[0]
            self.__from[alias] = resource_type
        else:
            raise ValueError(f"The FROM clause {string} couldn't be parsed properly")

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
        item_parsed = re.split(create_mask("ON"), string)
        assert len(item_parsed) == 2, f"There was a problem with the JOIN statement: {string}"
        self.__from_parser(item_parsed[0])

        join_conditions = re.split(create_mask("=", optional_spaces=True), item_parsed[1])
        assert (
            len(join_conditions) == 2
        ), f"The JOIN condition {join_conditions} couldn't be parsed properly"

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
        item_parsed = re.split(create_mask("AND"), string)
        for where_condition in item_parsed:
            condition_parsed = re.split(
                create_mask("=", keep_separators=True, optional_spaces=True), where_condition
            )
            if len(condition_parsed) != 3:
                condition_parsed = re.split(
                    create_mask(PREFIX, keep_separators=True), where_condition
                )
            assert (
                len(condition_parsed) == 3
            ), f"The WHERE condition {where_condition} couldn't be parsed properly"
            alias, where_rule = re.split(r"\.", condition_parsed[0], 1)
            quotes_match = re.search(r"^['\"](.*)['\"]$", condition_parsed[2])
            value = quotes_match.group(1) if quotes_match else condition_parsed[2]

            if condition_parsed[1] in PREFIX:
                prefix = condition_parsed[1]
                self.__where[alias][where_rule] = {prefix: value}
            else:
                self.__where[alias][where_rule] = value

    def __order_by_parser(self, string):
        raise NotImplementedError("The ORDER BY keyword is not supported for the moment.")

    def __group_by_parser(self, string):
        raise NotImplementedError("The ORDER BY keyword is not supported for the moment.")

    def __union_parser(self, string):
        raise NotImplementedError("The UNION keyword is not supported for the moment.")

    def __limit_parser(self, string):
        raise NotImplementedError("The LIMIT keyword is not supported for the moment.")
