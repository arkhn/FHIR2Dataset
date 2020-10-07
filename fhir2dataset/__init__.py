from fhir2dataset.query import Query  # noqa
from fhir2dataset.fhirrules_getter import FHIRRules  # noqa
from fhir2dataset.parser import Parser  # noqa


def sql(sql_query):
    parser = Parser()
    config = parser.from_sql(sql_query)
    query = Query()
    query.from_config(config)
    query.execute()
    df = query.main_dataframe
    return df.reset_index(drop=True)
