import pytest

from fhir2dataset.parser import Parser  # noqa


@pytest.mark.parametrize(
    "sql_query",
    [
        "SELECT Patient.name.family FROM Patient",
        "SELECT Patient.name.family FROM Patient;",
        "SELECT p.name.family FROM Patient as p",
        "SELECT p.name.family FROM Patient as p;",
        "SELECT Patient.name.family FROM Patient WHERE Patient.birthdate=1900",
        "SELECT Patient.name.family, Patient.address.city FROM Patient",
        """
SELECT Patient.name.family
FROM Patient
;""",
        """
    SELECT Patient.name.family
      FROM Patient
;""",
    ],
)
def test_select(sql_query):
    Parser().from_sql(sql_query)


def test_from():
    sql_query = "SELECT Patient.name.family FROM Patient AS p"
    with pytest.raises(ValueError):
        Parser().from_sql(sql_query)

    sql_query = "SELECT p.Patient.name.family FROM Patient"
    with pytest.raises(ValueError):
        Parser().from_sql(sql_query)


@pytest.mark.parametrize(
    "sql_query",
    [
        "SELECT p.name.family FROM Patient AS p WHERE p.birthdate=1900-01-01",
        "SELECT p.name.family FROM Patient AS p WHERE p.birthdate =1900-01-01",
        "SELECT p.name.family FROM Patient AS p WHERE p.birthdate= 1900-01-01",
        "SELECT p.name.family FROM Patient AS p WHERE p.birthdate = 1900-01-01",
        "SELECT p.name.family FROM Patient AS p WHERE p.birthdate = 1900-01-01 AND p.gender = 'female'",  # noqa
        """
    SELECT
    Patient.gender
    From Patient
    where Patient.birthdate=ge2000-01-01 and Patient.birthdate=le2000-01-31""",
    ],
)
def test_where(sql_query):
    Parser().from_sql(sql_query)
