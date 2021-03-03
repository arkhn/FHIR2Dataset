import re

import pandas as pd

from fhir2dataset.fhirrules import FHIRRules  # noqa
from fhir2dataset.parser import Parser  # noqa
from fhir2dataset.query import Query  # noqa


def sql(sql_query: str, fhir_api_url: str = None, token: str = None) -> pd.DataFrame:
    """Interpret a SQL-like query and query a FHIR api

    Arguments:
        sql_query (str): A query in a SQL-like syntax
        fhir_api_url (str): the base url of the FHIR server (e.g. http://hapi.fhir.org/baseR4/)
        token (str): a Bearer Auth token

    Returns:
        pd.Dataframe: the result of the query in a tabular format
    """
    config = Parser().from_sql(sql_query)
    query = Query(fhir_api_url=fhir_api_url, token=token).from_config(config)
    df = query.execute()
    # rename the columns to match the sql syntax
    # patient:Patient.name.given -> patient.name.given
    df = df.rename(lambda x: re.sub("\:\w+\.", ".", x), axis="columns")  # noqa
    return df
