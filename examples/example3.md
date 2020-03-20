## Example 3

> **Question:** Get the number of patients currently in intensive care unit because of Coronavirus

Note that we use the following SNOMED CT codes:
- 309904001: Intensive care unit (environment)
- 840546002: Exposure to severe acute respiratory syndrome coronavirus 2 (event)
- _(840539006: Disease caused by severe acute respiratory syndrome coronavirus 2 (disorder))_

Config file
```json
{
  "select": {
    "count": [ # not sure about this
      "patient",
    ]
  },
  "from": {
    "Encounter": "encounter",
    "Patient": "patient"
  },
  "join": {
    "encounter": {
      "subject": "patient"
    }
  },
  "where": {
    "encounter": {
      "type": "162673000",
      "reason-code": "840546002",
      "status": "in-progress"
    }
  }
}
```

Python syntax suggestion (slightly different of ex 1 and 2, using classes)
```python
Query
.select(
  count(Patient),
)
.from(Encounter, Patient)
.join(Encounter.subject=Patient)
.where(
  Encounter.type="162673000",
  Encounter.reason_code="840546002",
  Encounter.status="in-progress"
)
```

URL
```
http://hapi.fhir.org/baseR4/Encounter?type=162673000&status=in-progress&reason-code=840546002&_include=Encounter:subject
```

And some local treatment to:
- count all the patients resources returned


_Here is a similar URL but which returns some samples of data for testing_
```
http://hapi.fhir.org/baseR4/Encounter?type=OKI&status=in-progress&reason-code=1372004&_include=Encounter:subject
```
