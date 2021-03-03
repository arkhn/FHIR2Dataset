from fhir2dataset.graphquery import GraphQuery
from fhir2dataset.parser import Parser
from fhir2dataset.query import Query


def test_graphquery():
    sql_query = """
    SELECT
    Patient.identifier.type.coding,
    Patient.name.family,
    Patient.birthDate
    FROM Patient
    INNER JOIN Practitioner
    ON Patient.general-practitioner = Practitioner.id
    WHERE Patient.birthdate=ge2001-01-01
    """

    config = Parser().from_sql(sql_query)
    query = Query().from_config(config)
    graph_query = GraphQuery(fhir_api_url=query.fhir_api_url, fhir_rules=query.fhir_rules)
    graph_query.build(**query.config)
    graph = graph_query.resources_by_alias

    assert len(graph) == 2

    assert len(graph["Patient"].elements.elements) == 6
    assert len(graph["Practitioner"].elements.elements) == 1

    assert len(graph["Patient"].elements.where(goal="join")) == 1
