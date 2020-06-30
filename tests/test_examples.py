import os
import json
import sys
import logging
import pytest

sys.path.append(".")
from fhir2dataset.query import Query
from tools import create_resource_test

log_format = "[%(asctime)s] [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)


@pytest.mark.parametrize(
    "dirname, fhir_api_url",
    [
        ("tests/1", "http://hapi.fhir.org/baseR4/"),
        ("tests/2", "http://hapi.fhir.org/baseR4/"),
        ("tests/3", "http://hapi.fhir.org/baseR4/"),
        ("tests/1", "http://hapi.fhir.org/baseR4/"),
        ("tests/5", "http://hapi.fhir.org/baseR4/"),
    ],
)
def test_resources_in_dataframe(dirname, fhir_api_url):
    create_resource_test(dirname, fhir_api_url)
    with open(os.path.join(dirname, "config.json")) as json_file:
        config = json.load(json_file)
    with open(os.path.join(dirname, "infos_test", "config_checks.json")) as json_file:
        checks = json.load(json_file)
    with open(os.path.join(dirname, "infos_test", "info_hapi.json")) as json_file:
        info_hapi = json.load(json_file)

    query = Query(fhir_api_url)
    query.from_config(config)
    query.execute()
    df = query.main_dataframe

    lines = checks["line"]
    for line in lines:
        cols = []
        conditions = []
        for alias, filename in line:
            cols.append(f"{alias}:id")
            conditions.append(info_hapi[filename])
        condition = " & ".join(
            [f"(df['{col}'].str.contains('{cond}'))" for col, cond in zip(cols, conditions)]
        )
        logging.info(condition)
        result = df[eval(condition)]
        logging.info(result)
        assert len(result.index) >= 1, f"{dirname} failed"


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_resources_in_dataframe("tests/1", "http://hapi.fhir.org/baseR4/")
