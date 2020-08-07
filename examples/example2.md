## Example 2

> **Question:** Get clinical information about patients that had a general examination because of Coronavirus
>
> Here we get diagnosis codes for finished encounters. We get the period of the encounter and some information about the patient such as his age, gender and if he is alive.

Note that we use the following SNOMED CT codes:
- 162673000: General examination of patient (procedure)
- 840546002: Exposure to severe acute respiratory syndrome coronavirus 2 (event)
- _(840539006: Disease caused by severe acute respiratory syndrome coronavirus 2 (disorder))_

SQL query : 
```
SELECT patient.birthdate, patient.gender, patient.deceasedBoolean, encounter.period.start, encounter.period.end, encounter.diagnosis, condition.code.coding.system, condition.code.coding.code, condition.code.coding.display 
FROM Patient AS patient, Encounter AS encounter, Condition AS condition
INNER JOIN Condition AS condition ON condition.encounter = encounter.id INNER JOIN Encounter AS encounter ON encounter.subject = patient.id 
WHERE encounter.type = "162673000" AND encounter.reason-code="840546002" AND encounter.status="finished"
```

Config file :
```json
{
    "select": {
        "patient": [
            "birthdate",
            "gender"
        ],
        "encounter": [
            "period.start",
            "period.end"
        ],
        "condition": [
            "code.coding.display"
        ]
    },
    "from": {
        "Condition": "condition",
        "Encounter": "encounter",
        "Patient": "patient"
    },
    "join": {
        "inner": {
            "condition": {
                "encounter": "encounter"
            },
            "encounter": {
                "subject": "patient"
            }
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
Dataset :
```
patient.birthdate | patient.gender | encounter.period.start | 
_____________________________________________________________

1998-05-07        | female         | 2020-04-03


encounter.period.end | condition.code.coding.display 
______________________________________________________

2020-04-18           | Fever                          
```