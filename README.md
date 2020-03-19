# FHIR2Dataset

Transform FHIR to dataset for ML applications

## Example 1

In the `from` object, the key should be FHIR resources and the value is the name that we will use in the `select` and `where` (same as SQL `SELECT pat.id from Patient as pat`)

Config file
```json
{
  "select": {
    "patient": [
      "gender",
      "name.given"
    ]
  },
  "from": {
    "Patient": "patient"
  },
  "where": {
    "patient" : {
      "birthdate": {"ge": "2000-01-01"}
    }
  }
}
```

Python syntax suggestion
```python
Query
.select("patient.gender", "patient.name.given")
.from(Patient="patient")
.where("patient.birthdate>2000-01-01")
```

URL
```
/Patient?birthdate=>2000-01-01
```
And some local treatment to extract `patient.gender` and `patient.name.given`, using http://objectpath.org/
 

## Example 2

Note that http://loinc.org|55284-4 corresponds to blood pressure.

Config file
```json
{
  "select": {
    "observation": [
      "component.valueQuantity.value"
    ],
    "patient": [
      "birthdate",
      "gender"
    ]
  },
  "from": {
    "Patient": "patient",
    "Observation": "observation"
  },
  "join": {
    "observation": {
      "subject": "patient"
    }
  },
  "where": {
    "patient" : {
      "birthdate": {"ge": "1970"}
    },
    "observation": {
      "code": "http://loinc.org|55284-4"
    }
  }
}
```

Python syntax suggestion
```python
Query
.select(
  "observation.component.valueQuantity.value",
  "patient.birthdate",
  "patient.gender")
.from(Patient="patient", Observation="observation")
.join("observation.subject=patient")
.where(
  "observation.code=http://loinc.org|55284-4"
  "patient.birthdate>1970"
)
```

URL
```
http://hapi.fhir.org/baseR4/Observation?subject:Patient.birthdate=gt1970&code=http://loinc.org|55284-4&_include=Observation:subject
```
And some local treatment to:
- Bind in the response bundle the Patients with the Observation.subject references
- extract `observation.component.valueQuantity.value`, `observation.subject.birthdate`, `observation.subject.gender`

using http://objectpath.org/
