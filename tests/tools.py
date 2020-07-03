import requests
import json
import os
import sys
import logging


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
        logging.info(f"The resource hasn't been created\n" f"{status_code}")
    try:
        with open(path_info) as json_file:
            info = json.load(json_file)
    except:
        info = dict()
    info[filename] = id_resource
    with open(path_info, "w") as outfile:
        json.dump(info, outfile)
    return response


def load(path):
    with open(path) as json_file:
        data = json.load(json_file)
    return data


def create_resource_test(path_test, fhir_api_url="http://hapi.fhir.org/baseR4/"):
    path_config = os.path.join(path_test, "infos_test", "config_resources_creation.json")
    config = load(path_config)

    resources_bodies = dict()
    path_resources = os.path.join(path_test, "resources")
    for filename in os.listdir(path_resources):
        body = load(os.path.join(path_resources, filename))
        resources_bodies[filename] = body

    path_info_hapi = os.path.join(path_test, "infos_test", "info_hapi.json")

    for filename in config:
        body = resources_bodies[filename]
        update_resource(fhir_api_url, body, filename, path_info_hapi)
