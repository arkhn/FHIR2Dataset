import json
import logging
import os

import pytest

from fhir2dataset.query import Query
from tests.tools import delete_resource_test

log_format = "[%(asctime)s] [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)


@pytest.mark.parametrize(
    "dirname, fhir_api_url",
    [("tests/empty", "http://hapi.fhir.org/baseR4/")],
)
def test_dataframe_empty(dirname, fhir_api_url):
    delete_resource_test(dirname, fhir_api_url=fhir_api_url)
    with open(os.path.join(dirname, "config.json")) as json_file:
        config = json.load(json_file)

    query = Query(fhir_api_url)
    query.from_config(config)
    query.execute(debug=True)
    df = query.main_dataframe

    assert df.empty
