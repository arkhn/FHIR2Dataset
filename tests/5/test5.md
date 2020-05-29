Knowing that the resources are linked together by references according to the attached image, I wish to return Condition, AllergyIntolerance, Patient and Practitioner resources that meet all of the following conditions:

* patients were born in 1970

(associated search parameter of the resource Patient : birthdate=1970)

* they've been diagnosed allergic to Cashew nuts

(associated search parameter of the resource AllergyIntolerance: code=http://snomed.info/sct|227493005)

* the source of the information about the allergy is a practioner who lives in france (associated search parameter of the resource Practitioner: address-state=france)
* these patients have already had fever (associated search parameter of the resource Condition: code=http://snomed.info/sct|386661006)