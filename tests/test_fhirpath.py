import pytest
import sys
from dataclasses import asdict
from dacite import from_dict

from fhir2dataset.data_class import Elements, Element
from fhir2dataset.fhirpath import multiple_search_dict


@pytest.fixture()
def resources():
    resources = [
        {
            "resourceType": "Observation",
            "id": "f001",
            "text": {
                "status": "generated",
                "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\"><p><b>Generated Narrative with Details</b></p><p><b>id</b>: f001</p><p><b>identifier</b>: 6323 (OFFICIAL)</p><p><b>status</b>: final</p><p><b>code</b>: Glucose [Moles/volume] in Blood <span>(Details : {LOINC code '15074-8' = 'Glucose [Moles/volume] in Blood', given as 'Glucose [Moles/volume] in Blood'})</span></p><p><b>subject</b>: <a>P. van de Heuvel</a></p><p><b>effective</b>: 02/04/2013 9:30:10 AM --&gt; (ongoing)</p><p><b>issued</b>: 03/04/2013 3:30:10 PM</p><p><b>performer</b>: <a>A. Langeveld</a></p><p><b>value</b>: 6.3 mmol/l<span> (Details: UCUM code mmol/L = 'mmol/L')</span></p><p><b>interpretation</b>: High <span>(Details : {http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation code 'H' = 'High', given as 'High'})</span></p><h3>ReferenceRanges</h3><table><tr><td>-</td><td><b>Low</b></td><td><b>High</b></td></tr><tr><td>*</td><td>3.1 mmol/l<span> (Details: UCUM code mmol/L = 'mmol/L')</span></td><td>6.2 mmol/l<span> (Details: UCUM code mmol/L = 'mmol/L')</span></td></tr></table></div>",
            },
            "identifier": [
                {
                    "use": "official",
                    "system": "http://www.bmc.nl/zorgportal/identifiers/observations",
                    "value": "6323",
                }
            ],
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "15074-8",
                        "display": "Glucose [Moles/volume] in Blood",
                    }
                ]
            },
            "subject": {"reference": "Patient/f001", "display": "P. van de Heuvel"},
            "effectivePeriod": {"start": "2013-04-02T09:30:10+01:00"},
            "issued": "2013-04-03T15:30:10+01:00",
            "performer": [{"reference": "Practitioner/f005", "display": "A. Langeveld"}],
            "valueQuantity": {
                "value": 6.3,
                "unit": "mmol/l",
                "system": "http://unitsofmeasure.org",
                "code": "mmol/L",
            },
            "interpretation": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": "H",
                            "display": "High",
                        }
                    ]
                }
            ],
            "referenceRange": [
                {
                    "low": {
                        "value": 3.1,
                        "unit": "mmol/l",
                        "system": "http://unitsofmeasure.org",
                        "code": "mmol/L",
                    },
                    "high": {
                        "value": 6.2,
                        "unit": "mmol/l",
                        "system": "http://unitsofmeasure.org",
                        "code": "mmol/L",
                    },
                }
            ],
        }
    ]
    return resources


@pytest.fixture()
def elements():
    elements = Elements(
        [
            Element(col_name="code", fhirpath="Observation.code"),
            Element(col_name="subject reference", fhirpath="Observation.subject.reference"),
        ]
    )
    return elements


@pytest.fixture()
def answers():
    return [
        [
            [
                {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "15074-8",
                            "display": "Glucose [Moles/volume] in Blood",
                        }
                    ]
                }
            ],
            ["Patient/f001"],
        ]
    ]


def test_multiple_search_dict(resources, elements, answers):
    elements_empty = asdict(elements)
    data_dict_resources = multiple_search_dict(resources, elements_empty)

    for idx_resource, data_dict in enumerate(data_dict_resources):
        elements = from_dict(data_class=Elements, data=data_dict)
        print(elements)
        for idx, element in enumerate(elements.elements):
            assert element.value == answers[idx_resource][idx]
