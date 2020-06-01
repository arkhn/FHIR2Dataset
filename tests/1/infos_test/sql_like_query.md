SELECT patient.gender, patient.name.given, patient.birthDate, condition.verificationStatus, practitioner.name

FROM Condition as condition
INNER JOIN Patient as patient
ON condition.subject.reference = patient.id
INNER JOIN Practitioner as practitioner
ON condition.asserter.reference = practitioner.id

WHERE practitioner.family = "van den broek"
AND patient.family = "Smith"
AND condition.verification-status = "confirmed"