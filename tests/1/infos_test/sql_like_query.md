SELECT patient.gender, patient.name.given, patient.birthDate, condition.verificationStatus, practitioner.name

FROM Condition AS condition
INNER JOIN Patient AS patient
ON condition.subject = patient.id
INNER JOIN Practitioner AS practitioner
ON condition.asserter = practitioner.id

WHERE practitioner.family = "van den broek"
AND patient.family = "Smith"
AND condition.verification-status = "confirmed"
