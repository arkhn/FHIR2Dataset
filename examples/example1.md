## Example 1

> **Question:** Select the gender and name for patients born after 2000

In the `from` object, the key should be FHIR resources and the value is the name that we will use in the `select` and `where` (same as SQL `SELECT pat.id from Patient as pat`)

SQL query : 
```
SELECT patient.gender, patient.name.given
FROM Patient as patient
WHERE patient.birthadate = "gt": "2000-01-01"
```
The request can also be implemented as a JSON query. 

JSON query:

```json
{"select":{
    "patient":[
        "gender",
        "name.given"
    ]
},
"from":{
    "patient":"Patient"
},
"where":{
    "patient":{
        "birthdate":{
            "gt": "2000-01-01"
        }
    }
}}
```

Dataset :

```
patient.id | patient.gender | patient.name.given | patient.birthdate
____________________________________________________________________

pat_1      | female         | [Marie, Mell]      | 2000-01-01
____________________________________________________________________

pat_2      | male           | [Thomas]           | 2000-05-03

```