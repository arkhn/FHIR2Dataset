SELECT patient.name.family, patient.birthDate, practitioner.name.family, practitioner.address, allergy.code.display, condition.code.coding.display, condition.severity.coding.display

FROM AllergyIntolerance as allergy
INNER JOIN Patient as patient ON allergy.patient.reference = patient.id
INNER JOIN Practitioner as practitioner ON allergy.asserter.reference = practitioner.id
INNER JOIN Condition as condition ON condition.subject.reference = patient.id

WHERE patient.birthdate gt "1970"
AND allergy.code = "http://snomed.info/sct|22749300"
AND practitioner.address-city = "paris"
AND condition.code = "http://snomed.info/sct|386661006"