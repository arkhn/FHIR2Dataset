from fhir2dataset import Query, FHIRRules, FHIR2DatasetParser
import json
import pprint
import pandas as pd
import os

from fhir2dataset.graph_tools import join_path
from fhir2dataset.url_builder import URLBuilder
from fhir2dataset.visualization_tools import custom_repr
from fhir2dataset.data_class import show_tree

pp = pprint.PrettyPrinter(indent=1)

dirname = 'tests/5'
filename_config = 'config.json'
filename_question = 'question.md'
filename_sql_like_query = 'infos_test/sql_like_query.md'


if __name__ == "__main__":
    with open(os.path.join(dirname, filename_config)) as json_file:
        config = json.load(json_file)
    with open(os.path.join(dirname, filename_question), 'r') as mardown_file:
        question = mardown_file.read()
    with open(os.path.join(dirname, filename_sql_like_query), 'r') as mardown_file:
        sql_like_query = mardown_file.read()
    print("--- SQL query ---")
    print(sql_like_query)
    print("\n---CONFIG---")
    pp.pprint(config)
    parser = FHIR2DatasetParser()
    config_from_parser = parser.parse(sql_like_query)
    print("\n---PARSED CONFIG---")
    pp.pprint(config_from_parser)
    fhir_api_url = 'http://hapi.fhir.org/baseR4/'
    # fhir_rules can be instantiated only once and then used for all the queries
    fhir_rules = FHIRRules(fhir_api_url=fhir_api_url)
