import logging

import fhir2dataset as query
from fhir2dataset.api import ApiRequest
from fhir2dataset.data_class import Element, Elements


def test_get_all():
    """
    Test that the next link is used correctly
    """
    PAGE_SIZE = query.api.PAGE_SIZE

    query.api.PAGE_SIZE = 30
    url = "http://hapi.fhir.org/baseR4/Patient?birthdate=2000-01-01"
    elements = Elements()
    elements.append(Element("gender", "Patient.gender"))
    call_api = ApiRequest(url, elements)
    call_api.get_all()

    if len(call_api.df) < query.api.PAGE_SIZE:
        logging.warn(
            f"test_get_all couldn't be tested properly. Only {len(call_api.df)} "
            f"results returned for page size {query.api.PAGE_SIZE}."
        )

    query.api.PAGE_SIZE = PAGE_SIZE
