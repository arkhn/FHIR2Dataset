# FHIR2Dataset

Transform FHIR to dataset for ML applications

## FHIR2Dataset in Detail

This project is still under development.

This repo is a POC allowing to make a SQL query on a FHIR API and to retrieve tabular data. 

The SQL query is written in a parser and transformed into a URL to retrieve data from a FHIR API. In the end, the JSON type data will be returned as tabular data.

Initialization :

```
fhir_api_url = 'http://hapi.fhir.org/baseR4/'

fhir_rules=FHIRRules(fhir_api_url=fhir_api_url)

query = Query(fhir_api_url,fhir_rules=fhir_rules)

parser = FHIR2DatasetParser()
```

SQL request : 

```
SELECT (alias n°1).a, (alias n°1).b, (alias n°1).c, (alias n°2).a FROM (Resource type 1) as (alias n°1)
INNER JOIN (Resource type 2) as (alias n°2)
ON (alias n°1).d = (alias n°2)
INNER JOIN (Resource type 3) as (alias n°3)
ON (alias n°2).b = (alias n°3) WHERE (alias n°2).c = "value 1"
AND (alias n°2).d = "value 2"
AND (alias n°3).a = "value 3"
AND (alias n°3).b = "value 4"
```
The request can also be implemented as a JSON query. 

Similar JSON query : 

```json
{"select":{
    "alias n°1":[
        "a",
        "b",
        "c"
    ],
    "alias n°2":[
        "a"
    ]
},
"from":{
    "alias n°1":"Resource type 1",
    "alias n°2":"Resource type 2",
    "alias n°3":"Resource type 3"
},
"join":{
    "inner": {
        "alias n°1":{
            "d":"alias n°2"

        },
        "alias n°2":{
            "b":"alias n°3"
        }

    }
},
"where":{
    "alias n°2":{
        "c":"value 1",
        "d":"value 2"
    },
    "alias n°3":{
        "a":"value 3",
        "b":"value 4"
    }
}}
```

## Installation

After cloning this repository, you can install the required dependencies

```
pip install -r requirements.txt
npm install --prefix ./fhir2dataset/metadata
```

For usage, refer to this [turorial](https://htmlpreview.github.io/?https://github.com/arkhn/FHIR2Dataset/blob/query_tests/examples/tutorial.html) and then this [Jupyer Notebook](examples/example.ipynb)

## Examples

Check out examples of queries and how they are transformed in call to the FHIR api!

-   [Select the gender and name for patients born after 2000](examples/example1.md)
-   [Get clinical information about patients that were in intensive care unit because of Coronavirus](examples/example5.md)

## Contributing

The following commands on a terminal and in your virtual environment allow you to do some minimal local testing before each commit:

```
pip install -r requirements-dev.txt
pre-commit install
```

If you ever want to delete them you just have to do:

```
pre-commit clean
```

## Publish

First, you need to have `twine` installedd

```
pip install --user --upgrade twine
```

Make sure you have bumped the version number in `setup.py`, then run the following:

```
python setup.py sdist bdist_wheel
python -m twine upload dist/*
```
