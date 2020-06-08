import os
import json
import sys
import logging

sys.path.append(".")

from outils import test_resources_in_dataframe

log_format = "[%(asctime)s] [%(levelname)s] - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)


def test_1():
    dirname = "tests/1"
    fhir_api_url = "http://hapi.fhir.org/baseR4/"
    path_rules = "data"

    test_resources_in_dataframe(dirname, fhir_api_url, path_rules)


def test_2():
    dirname = "tests/2"
    fhir_api_url = "http://hapi.fhir.org/baseR4/"
    path_rules = "data"

    test_resources_in_dataframe(dirname, fhir_api_url, path_rules)


def test_3():
    dirname = "tests/3"
    fhir_api_url = "http://hapi.fhir.org/baseR4/"
    path_rules = "data"

    test_resources_in_dataframe(dirname, fhir_api_url, path_rules)


def test_4():
    dirname = "tests/4"
    fhir_api_url = "http://hapi.fhir.org/baseR4/"
    path_rules = "data"

    test_resources_in_dataframe(dirname, fhir_api_url, path_rules)


def test_5():
    dirname = "tests/5"
    fhir_api_url = "http://hapi.fhir.org/baseR4/"
    path_rules = "data"

    test_resources_in_dataframe(dirname, fhir_api_url, path_rules)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    test_1()
    test_2()
    test_3()
    test_4()
    test_5()
