"""classes representing the different types of information manipulated in FHIR2Dataset
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from fhir2dataset.tools.visualization import custom_repr

logger = logging.getLogger(__name__)


@dataclass
class SearchParameter:
    code: Optional[str] = field(default=None)
    fhirpath: Optional[str] = field(default=None)
    resource_types: Optional[List[str]] = field(default=None)
    prefix: Optional[str] = field(default=None)
    value: Optional[str] = field(default=None)


@dataclass
class Element:
    """unit entity that can be found in a fhir instance in json format using fhirpath or in a table in the col_name column.

    An element is destined to be associated with a single value. For example, if we want to retrieve the patient id of a bundle containing 2 patients, we will have to create 2 element instances.
    """  # noqa

    col_name: str
    fhirpath: str
    goal: str = field(default="select")  # select, where or join
    concat_type: Optional[str] = field(default="cell")
    search_parameter: Optional["SearchParameter"] = field(default=None)


@dataclass
class Elements:
    """collection allowing to group together elements"""

    elements: List[Element] = field(default_factory=list)

    def append(self, x):
        self.elements.append(x)

    def where(self, goal):
        return [element for element in self.elements if element.goal == goal]

    # FIXME: Need FHIR2Dataset#96
    # def compute_forest_fhirpaths(self):
    #     forest = Forest()
    #     for fhirpath in [element.fhirpath for element in self.elements]:
    #         forest.add_fhirpath(fhirpath)
    #     forest.simplify_trees()
    #     forest.parse_fhirpaths()
    #     self.forest = forest
    #     self.forest_dict = forest.create_forest_dict()


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
    searchparam_parent: Optional[str] = field(default=None)
    join_how: str = field(default="inner")
    searchparam_prefix: Optional[dict] = field(default=None)
