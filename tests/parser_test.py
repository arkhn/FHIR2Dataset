import pytest

import fhir2dataset


def test_select():
    sql_query = "SELECT Patient.name.family FROM Patient WHERE Patient.birthdate=1900"
    assert len(fhir2dataset.sql(sql_query)) > 0

    sql_query = (
        "SELECT Patient.name.family, Patient.address.city FROM Patient WHERE Patient.birthdate=1900"
    )
    assert len(fhir2dataset.sql(sql_query)) > 0

    sql_query = (
        "SELECT Patient.name.family, Patient.address.city FROM Patient WHERE Patient.birthdate=1900"
    )
    assert len(fhir2dataset.sql(sql_query)) > 0


def test_from():
    sql_query = "SELECT p.name.family FROM Patient AS p WHERE p.birthdate=1900"
    assert len(fhir2dataset.sql(sql_query)) > 0

    sql_query = "SELECT Patient.name.family FROM Patient AS p WHERE Patient.birthdate=1900"
    with pytest.raises(AssertionError):
        fhir2dataset.sql(sql_query)

    sql_query = "SELECT p.Patient.name.family FROM Patient WHERE Patient.birthdate=1900"
    with pytest.raises(AssertionError):
        fhir2dataset.sql(sql_query)


def test_where():
    sql_query = "SELECT p.name.family FROM Patient AS p WHERE p.birthdate=1900"
    assert len(fhir2dataset.sql(sql_query)) > 0

    sql_query = "SELECT p.name.family FROM Patient AS p WHERE p.birthdate =1900"
    assert len(fhir2dataset.sql(sql_query)) > 0

    sql_query = "SELECT p.name.family FROM Patient AS p WHERE p.birthdate = 1900"
    assert len(fhir2dataset.sql(sql_query)) > 0

    sql_query = (
        "SELECT p.name.family FROM Patient AS p WHERE p.birthdate = 1900 AND p.gender = 'female'"
    )
    assert len(fhir2dataset.sql(sql_query)) > 0
