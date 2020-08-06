SELECT patient.family, patient.birthdate, patient.id, practitioner.family, practitioner.address, practitioner.id, allergy.code, allergy.id, condition.code, condition.severity, condition.id

FROM AllergyIntolerance AS allergy
INNER JOIN Patient AS patient ON allergy.patient = patient.id
INNER JOIN Practitioner AS practitioner ON allergy.asserter = practitioner.id
INNER JOIN Condition AS condition ON condition.subject = patient.id

WHERE patient.birthdate = "1976"
AND allergy.code = "http://snomed.info/sct|22749300"
AND practitioner.address-city = "paris"
AND condition.code = "http://snomed.info/sct|386661006"
