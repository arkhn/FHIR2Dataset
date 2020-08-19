# FHIR2Dataset

Transform FHIR to dataset for ML applications

## FHIR2Dataset in Detail

This repo allows to make a SQL query on a FHIR API and to retrieve tabular data.

_FHIR2Dataset is still under active development!_

## Installation

### With pip

`pip install fhir2dataset`

### From source

After cloning this repository, you can install the required dependencies

```
pip install -r requirements.txt
npm install --prefix ./fhir2dataset/metadata
```

For usage, refer to this [turorial](https://htmlpreview.github.io/?https://github.com/arkhn/FHIR2Dataset/blob/query_tests/examples/tutorial.html) and then this [Jupyer Notebook](examples/example.ipynb)

## Getting started

Two possible ways to enter the query : as a SQL query or as a JSON config file

**SQL query as entry**

```
from fhir2dataset import Query, FHIRRules, FHIR2DatasetParser

fhir_api_url = 'http://hapi.fhir.org/baseR4/'
fhir_rules = FHIRRules(fhir_api_url=fhir_api_url)
query = Query(fhir_api_url, fhir_rules=fhir_rules)
parser = FHIR2DatasetParser()
```

```
sql_like_query = "SELECT (alias n°1).a, (alias n°1).b, (alias n°1).c, (alias n°2).a FROM (Resource type 1) as (alias n°1)
INNER JOIN (Resource type 2) as (alias n°2)
ON (alias n°1).d = (alias n°2)
INNER JOIN (Resource type 3) as (alias n°3)
ON (alias n°2).b = (alias n°3) WHERE (alias n°2).c = "value 1"
AND (alias n°2).d = "value 2"
AND (alias n°3).a = "value 3"
AND (alias n°3).b = "value 4""
```

```
config_from_parser = parser.parse(sql_like_query)
query.from_config(config_from_parser)
query.execute()
df = query.main_dataframe
```

**JSON config file as entry**

```
from fhir2dataset.query import Query
from fhir2dataset.fhirrules_getter import FHIRRules

fhir_api_url = 'http://hapi.fhir.org/baseR4/'
fhir_rules = FHIRRules(fhir_api_url=fhir_api_url)
query = Query(fhir_api_url, fhir_rules=fhir_rules)
```

config.json :

```json
{
    "select": {
        "alias n°1": ["a", "b", "c"],
        "alias n°2": ["a"]
    },
    "from": {
        "alias n°1": "Resource type 1",
        "alias n°2": "Resource type 2",
        "alias n°3": "Resource type 3"
    },
    "join": {
        "inner": {
            "alias n°1": {
                "d": "alias n°2"
            },
            "alias n°2": {
                "b": "alias n°3"
            }
        }
    },
    "where": {
        "alias n°2": {
            "c": "value 1",
            "d": "value 2"
        },
        "alias n°3": {
            "a": "value 3",
            "b": "value 4"
        }
    }
}
```

```
# Enter in dirname the path of config.json
filename_config = 'config.json'

with open(os.path.join(dirname, filename_config)) as json_file:
    config = json.load(json_file)

query.from_config(config)
query.execute()
df = query.main_dataframe
```

## Examples

Check out examples of queries and how they are transformed in call to the FHIR api!

-   [Select the gender and name for patients born after 2000](examples/example1.md)
-   [Get clinical information about patients that were in intensive care unit because of Coronavirus](examples/example2.md)

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
