## Example 2

> **Question:** Get the pressure measures of patients born after 1970, together with their gender and birthdate

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
  "patient.gender"
)
.from(Patient="patient", Observation="observation")
.join("observation.subject=patient")
.where(
  "observation.code=http://loinc.org|55284-4",
  "patient.birthdate>1970"
)
```

URL 1
```
http://hapi.fhir.org/baseR4/Observation?subject:Patient.birthdate=gt1970&code=http://loinc.org|55284-4&_include=Observation:subject
```
And some local treatment to:
- Bind in the response bundle the Patients with the Observation.subject references
- extract `observation.component.valueQuantity.value`, `observation.subject.birthdate`, `observation.subject.gender`

using http://objectpath.org/

variant for url 1
```
http://hapi.fhir.org/baseR4/Observation?subject:Patient.birthdate=gt1970&code=http://loinc.org|55284-4&_include=Observation:subject:Patient
```