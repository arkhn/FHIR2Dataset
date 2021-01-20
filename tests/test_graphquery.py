import fhir2dataset as query


def test_double_where_condition():
    """
    Typically in time range, we use smthg like birthdate=ge2000-01-01&birthdate=le2000-10-02
    """
    sql_query = """
    SELECT
    Patient.gender
    From Patient
    where Patient.birthdate=ge2000-01-01 and Patient.birthdate=le2000-01-31
    """
    df = query.sql(
        sql_query=sql_query,
        fhir_api_url="http://hapi.fhir.org/baseR4/",
    )
    assert list(df.columns) == ["Patient.gender"]
    assert len(df.columns) < 1000, "Too many results returned, is the time range working?"
