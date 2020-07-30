"""classes representing the different types of information manipulated in FHIR2Dataset
"""
import logging
from collections import defaultdict
from pprint import pformat
from dataclasses import dataclass, field
from typing import Type, List, Optional

from fhir2dataset.visualization_tools import custom_repr


logger = logging.getLogger(__name__)


@dataclass
class SearchParameter:
    code: Optional[str] = field(default=None,)
    fhirpath: Optional[str] = field(default=None,)
    resource_types: Optional[List[str]] = field(default=None,)
    prefix: Optional[str] = field(default=None,)
    value: Optional[str] = field(default=None,)


@dataclass
class Element:
    """unit entity that can be found in a fhir instance in json format using fhirpath or in a table in the col_name column.

    An element is destined to be associated with a single value. For example, if we want to retrieve the patient id of a bundle containing 2 patients, we will have to create 2 element instances.
    """  # noqa

    col_name: str
    fhirpath: str
    goal: str = field(default="select",)
    value: Optional[list] = field(default=None,)
    concat_type: Optional[str] = field(default="cell",)
    search_parameter: Optional[SearchParameter] = field(default=None,)


@dataclass
class Elements:
    """collection allowing to group together elements
    """

    elements: List[Element] = field(default_factory=list)

    def append(self, x):
        self.elements.append(x)

    def get_subset_elements(self, goal):
        return [element for element in self.elements if element.goal == goal]


@dataclass
class ResourceAliasInfoBasic:
    alias: str
    resource_type: str
    elements: Elements() = field(default_factory=Elements())


class ResourceAliasInfo(ResourceAliasInfoBasic):
    def __repr__(self):
        return custom_repr(super().__repr__())


@dataclass
class EdgeInfo:
    parent: str
    child: str
    searchparam_parent: Optional[str] = field(default=None,)
    join_how: str = field(default="inner",)
    searchparam_prefix: Optional[dict] = field(default=None,)


class SearchParameters:
    def __init__(self, search_parameters: List[Type[SearchParameter]] = None):
        if search_parameters:
            self.items = search_parameters
        else:
            self.items = []
        self._init_data()

    def add(self, search_parameters):
        if isinstance(search_parameters, SearchParameter):
            self.items.append(search_parameters)
            self._add_data(search_parameters)
        elif isinstance(search_parameters, list):
            self.items.extend(search_parameters)
            for search_parameter in search_parameters:
                self._add_data(search_parameter)
        else:
            raise TypeError(
                f"{search_parameters} should be a list or a SearchParameter type instead of "
                f"{type(search_parameters)} type"
            )

    def searchparam_to_fhirpath(self, search_param: str, resource_type: str = "all"):
        """retrieves the fhirpath that allows to retrieve the element that is the object of a searchparam in a json instance (after the 'resource' key) of a resource of a certain type

        Arguments:
            resource_type {str} -- name of a resource type (e.g. 'Organization')
            search_param {str} -- name of a searchparam of this resource type (e.g. 'address-postalcode')

        Returns:
            str -- the fhirpath for retrieving the element that is the subject of the searchparam (e.g. 'address.postalCode')
        """  # noqa
        try:
            return self._data[search_param][resource_type]
        except KeyError:
            logger.warning(f"The searchparam '{search_param}' doesn't exist in the rules")
            return None

    def _init_data(self):
        self._data = defaultdict(lambda: defaultdict(dict))
        for search_parameter in self.items:
            self._add_data(search_parameter)

    def _add_data(self, search_parameter: Type[SearchParameter]):
        fhirpath = search_parameter.fhirpath
        data = self._data[search_parameter.code]
        for resource_type in search_parameter.resource_types:
            if resource_type not in data.keys():
                data[resource_type] = fhirpath
            else:
                raise ValueError(
                    f"the search parameter {search_parameter.code} is already recorded\n"
                    f"data already recorded: {pformat(self._data[search_parameter.code])}\n"
                    f"data given as argument: {search_parameter}\n"
                )
