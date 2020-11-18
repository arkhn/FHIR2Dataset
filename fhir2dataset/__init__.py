from fhir2dataset.query import Query  # noqa
from fhir2dataset.fhirrules_getter import FHIRRules  # noqa
from fhir2dataset.parser import Parser  # noqa

import re


def sql(sql_query, fhir_api_url=None, token=None):
    config = Parser().from_sql(sql_query)
    query = Query(fhir_api_url=fhir_api_url, token=token).from_config(config)
    query.execute()
    df = query.main_dataframe
    df = df.reset_index(drop=True)
    # rename the columns to match the sql syntax
    # patient:Patient.name.given -> patient.name.given
    df = df.rename(lambda x: re.sub("\:\w+\.", ".", x), axis="columns")  # noqa
    return df.reset_index(drop=True)
