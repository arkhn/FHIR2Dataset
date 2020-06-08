import requests
import json
import os
import sys
import logging

sys.path.append(".")
from query import Query

def update_resource(fhir_api_url, body, filename, path_info):
    id_resource = None

    type = body["resourceType"]
    id = body["id"]
    url = f"{fhir_api_url}{type}/{id}?"
    # logging.info(f"url: {url}")
    response = requests.put(url, json=body)
    status_code = response.status_code
    if status_code == 200 or status_code == 201:
        logging.info(f"The resource has successfully been created")
        id_resource = response.json()["id"]
    else:
        logging.info(
            f"The resource hasn't been created\n"
            f"{status_code}"
            )
    try:
        with open(path_info) as json_file:
            info = json.load(json_file)
    except:
        info = dict()
    info[filename] = id_resource
    with open(path_info, 'w') as outfile:
        json.dump(info, outfile)
    return response

def load(path):
    with open(path) as json_file:
        data = json.load(json_file)
    return data

def create_resource_test(path_test):
    fhir_api_url= 'http://hapi.fhir.org/baseR4/'
    
    path_config = os.path.join(path_test, 'infos_test', 'config_resources_creation.json')
    config = load(path_config)

    resources_bodies = dict()
    path_resources = os.path.join(path_test, 'resources')
    for filename in os.listdir(path_resources):
        body = load(os.path.join(path_resources, filename))
        resources_bodies[filename] = body


    path_info_hapi = os.path.join(path_test, 'infos_test', 'info_hapi.json')

    for filename in config:
        body = resources_bodies[filename]
        update_resource(fhir_api_url, body, filename, path_info_hapi)

def test_resources_in_dataframe(dirname, fhir_api_url, path_rules):
    create_resource_test(dirname)
    with open(os.path.join(dirname, "config.json")) as json_file:
        config = json.load(json_file)
    with open(
        os.path.join(dirname, "infos_test", "config_checks.json")
    ) as json_file:
        checks = json.load(json_file)
    with open(
        os.path.join(dirname, "infos_test", "info_hapi.json")
    ) as json_file:
        info_hapi = json.load(json_file)

    query = Query(fhir_api_url, path_rules)
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
                    [
                        f"(df['{col}'].str.contains('{cond}'))"
                        for col, cond in zip(cols, conditions)
                    ]
                )
        logging.info(condition)
        result = df[
            eval(
                condition
            )
        ]
        logging.info(result)
        assert len(result.index) >= 1, f"{dirname} failed"