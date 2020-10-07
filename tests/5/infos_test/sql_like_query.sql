SELECT patient.Patient.name.family,patient.Patient.name.given,patient.Patient.birthDate,patient.Patient.id,practitioner.Practitioner.name.family,practitioner.Practitioner.address.use,practitioner.Practitioner.address.line,practitioner.Practitioner.address.city,practitioner.Practitioner.id,allergy.AllergyIntolerance.code.coding.display,allergy.AllergyIntolerance.id,condition.Condition.code.coding.display,condition.Condition.severity.coding.display,condition.Condition.id

FROM AllergyIntolerance AS allergy
INNER JOIN Patient AS patient ON allergy.patient = patient.id
INNER JOIN Practitioner AS practitioner ON allergy.asserter = practitioner.id
INNER JOIN Condition AS condition ON condition.subject = patient.id

WHERE patient.birthdate = "1976"
AND allergy.code = "http://snomed.info/sct|22749300"
AND practitioner.address-city = "paris"
AND condition.code = "http://snomed.info/sct|386661006"
