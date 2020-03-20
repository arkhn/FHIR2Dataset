## Example 4

> **Question:** Get clinical information about patients that were in intensive care unit because of Coronavirus
>
> Here we get diagnosis codes for finished encounters. We get the period of the encounter and some information about the patient such as his age, gender and if he is alive.

Note that we use the following SNOMED CT codes:
- 309904001: Intensive care unit (environment)
- 840546002: Exposure to severe acute respiratory syndrome coronavirus 2 (event)
- _(840539006: Disease caused by severe acute respiratory syndrome coronavirus 2 (disorder))_

Config file
```json
{
  "select": {
    "patient": [
      "birthdate",
      "gender",
      "deceasedBoolean",
    ],
    "encounter": [
      "period.start",
      "period.end",
      "diagnosis"
    ],
    "condition": [
      "code.coding.system",
      "code.coding.code",
      "code.coding.display"
    ]
  },
  "from": {
    "Condition": "condition",
    "Encounter": "encounter",
    "Patient": "patient"
  },
  "join": {
    "condition": {
      "encounter": "encounter"
    },
    "encounter": {
      "subject": "patient"
    }
  },
  "where": {
    "encounter": {
      "type": "162673000",
      "reason-code": "840546002",
      "status": "finished"
    }
  }
}
```

Python syntax suggestion (slightly different of ex 1 and 2, using classes)
```python
Query
.select(
  Condition.code.coding.system,
  Condition.code.coding.code,
  Condition.code.coding.display,
  Encounter.period.start,
  Encounter.period.end,
  Encounter.diagnosis,
  Patient.birthdate,
  Patient.gender,
  Patient.deceasedBoolean
)
.from(Condition, Encounter, Patient)
.join(
  Condition.encounter=Encounter,
  Encounter.subject=Patient
)
.where(
  Encounter.type="162673000",
  Encounter.reason_code="840546002",
  Encounter.status="finished"
)
```

URL
```
http://hapi.fhir.org/baseR4/Condition?
encounter:Encounter.type=162673000&
encounter:Encounter.reason-code=840546002&
encounter:Encounter.status=finished&
_include=Encounter:encounter&_include:iterate=Patient:subject
```

And some local treatment to:
- Bind in the response bundle the Patients with the Encounter.subject references and the Encounters with the Condition.encounter references.
- extract `condition.code.coding.system, condition.code.coding.code, condition.code.coding.display, condition.encounter.period.start, condition.encounter.period.end, condition.encounter.diagnosis, condition.encounter.patient.birthdate, condition.encounter.patient.gender, condition.encounter.patient.deceasedBoolean`

_Note that because Condition also references the Patient subject, `_include:iterate` could also be replaced with `_include` and Condition would left joining directly Encounter + Patient._


_Here is a similar URL but which returns some samples of data for testing_
```
http://hapi.fhir.org/baseR4/Condition?
encounter:Encounter.type=185345009&
encounter:Encounter.reason-code=232353008&
encounter:Encounter.status=finished&
_include=Encounter:encounter&_include:iterate=Patient:subject
```
