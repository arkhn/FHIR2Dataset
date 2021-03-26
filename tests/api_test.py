import logging

import pandas as pd
import pytest

import fhir2dataset as query
from fhir2dataset.api import ApiCall, ApiRequest, BearerAuth, Response
from fhir2dataset.data_class import Element, Elements


def test_api_call_get_response():
    url = "http://hapi.fhir.org/baseR4/Patient"
    api_call = ApiCall(url=url)
    response = api_call._get_response(url)

    assert isinstance(response, Response)
    assert "http://hapi.fhir.org/baseR4" in response.next_url

    url = "http://hapi.fhir.org/baseR4/Demon"
    with pytest.raises(ValueError):
        api_call._get_response(url)

    url = "http://hapi.fhir.org/baseR4/Patient?lolz=1"
    with pytest.raises(ValueError):
        api_call._get_response(url)

    url = "http://hapi.fhir.org/baseR1/Patient"
    with pytest.raises(ValueError):
        api_call._get_response(url)


def test_api_call_get_count():
    url = "http://hapi.fhir.org/baseR4/Patient"
    api_call = ApiCall(url=url)
    total = api_call._get_count(url)
    assert isinstance(total, int)
    assert total > 0


def test_api_call_fix_next_url():
    url = "http://hapi.fhir.org/baseR4/Patient"
    api_call = ApiCall(url=url)
    fixed_url = api_call._fix_next_url(url)

    assert "_count" in fixed_url


@pytest.mark.parametrize(
    "bad_url, good_url",
    [
        (
            "http://arkhn.org/Patient?gender=male?param=value",
            "http://arkhn.org/Patient?gender=male&param=value",
        ),
        ("http://arkhn.org/Patient/?gender=male", "http://arkhn.org/Patient?gender=male"),
    ],
)
def test_api_fix_url(bad_url, good_url):
    fix_url = ApiCall._ApiCall__fix_url
    assert fix_url(bad_url) == good_url


def test_api_request_get_all():
    """
    Test that the next link is used correctly and that more than 1 page is fetched
    """
    PAGE_SIZE = query.api.PAGE_SIZE

    query.api.PAGE_SIZE = 30
    url = "http://hapi.fhir.org/baseR4/Patient?birthdate=2000-01-01"
    elements = Elements()
    elements.append(Element("gender", "Patient.gender"))
    call_api = ApiRequest(url, elements)
    results = call_api.get_all()

    if len(call_api.df) < query.api.PAGE_SIZE:
        logging.warn(
            f"test_get_all couldn't be tested properly. Only {len(call_api.df)} "
            f"results returned for page size {query.api.PAGE_SIZE}."
        )

    assert len(results) > query.api.PAGE_SIZE

    # restore the original PAGE_SIZE
    query.api.PAGE_SIZE = PAGE_SIZE


def test_api_request__get_data():
    url = "http://hapi.fhir.org/baseR4/Patient?birthdate=2000-01-01"
    elements = Elements()
    elements.append(Element("birthdate", "Patient.birthDate"))
    call_api = ApiRequest(url, elements)

    results = [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "23",
                "birthDate": "2000-01-01",
                "gender": "male",
            }
        },
        {
            "resource": {
                "resourceType": "Patient",
                "id": "24",
                "birthDate": "2000-01-01",
                "gender": "male",
            }
        },
    ]
    expected_tabular_results = pd.DataFrame({"birthdate": ["2000-01-01", "2000-01-01"]})

    tabular_results = call_api._get_data(results)

    assert (expected_tabular_results == tabular_results).all().bool()
