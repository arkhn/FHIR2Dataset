## Example 1

> **Question:** Select the gender and name for patients born after 2000

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
