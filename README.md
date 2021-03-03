# FHIR Query

Query any FHIR api using SQL to get tabular datasets.

## Usage

```python
import fhir2dataset as query
sql_query = """
SELECT Patient.name.family, Patient.address.city
FROM Patient
WHERE Patient.birthdate = 2000-01-01 AND Patient.gender = 'female'
"""
query.sql(sql_query)
```

```
100%|██████████| 1000/1000 [00:01<00:00, 16it/s]

    Patient.name.family        Patient.address.city
--------------------------------------------
0   Mozart                     Paris
1   Chopin                     London
2   Listz                      Vienna
...
```

FHIR Query is still under active development, feedback and contributions are welcome!

## Installation

`pip install fhir2dataset`

### From source

After cloning this repository, you can install the required dependencies

```bash
pip install -r requirements.txt
npm install --prefix ./fhir2dataset/tools/metadata
```

Check that the version of antlr4 is 4.8: `npm view antlr4 version`. If not, run `cd fhir2dataset/metadata && npm install antlr4@4.8.0`.

## Getting started

There are two possible ways to enter the query: as a SQL query or as a JSON config file

**SQL query**

You can define SQL queries of the following form:

```sql
SELECT alias_1.a, alias_1.b, alias_2.a
FROM Resource_1 AS alias_1
INNER JOIN Resource_2 AS alias_2 ON alias_1.d = alias_2
WHERE alias_1.c = value_1
AND alias_2.d = value_2
```

**Important note:** Attributes in the `SELECT` clause should be valid fhir paths, while attributes in the `WHERE` clause should be valid search parameters.

Note that we only support a subset of SQL keywords.

By default, FHIR Query will use the HAPI FHIR Api. But you can use your own api using the following syntax:

```python
import fhir2dataset as query

sql_query = "SELECT ..."

query.sql(
    sql_query=sql_query,
    fhir_api_url="https://api.awesome.fhir.org/baseR4/",
    token="<my token>"
)
```

To have more infos about the execution, you can enable logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

**JSON config file**

You can also use JSON configuration files.

```python
from fhir2dataset.query import Query
from fhir2dataset.fhirrules_getter import FHIRRules

fhir_api_url = 'http://hapi.fhir.org/baseR4/'
fhir_rules = FHIRRules(fhir_api_url=fhir_api_url)
query = Query(fhir_api_url, fhir_rules=fhir_rules)
```

`config.json`:

```json
{
  "select": {
    "alias_1": ["a", "b"],
    "alias_2": ["a"]
  },
  "from": {
    "alias_1": "Resource_1",
    "alias_2": "Resource_2"
  },
  "join": {
    "inner": {
      "alias_1": {
        "d": "alias_2"
      }
    }
  },
  "where": {
    "alias_1": {
      "c": "value_1"
    },
    "alias_2": {
      "d": "value_2"
    }
  }
}
```

```python
with open('/path/to/config.json') as json_file:
    config = json.load(json_file)

query = Query(fhir_api_url=fhir_api_url, token=token)
query = query.from_config(config)
query.execute()
```

For extended usage, you can refer to this [tutorial](https://htmlpreview.github.io/?https://github.com/arkhn/FHIR2Dataset/blob/query_tests/examples/tutorial.html) and then this [Jupyter Notebook](examples/example.ipynb)

### More Examples

Check out examples of queries and how they are transformed in call to the FHIR api!

- [Select the gender and name for patients born after 2000](examples/example1.md)
- [Get clinical information about patients that were in intensive care unit because of Coronavirus](examples/example2.md)

## Contributing

The following commands on a terminal and in your virtual environment allow you to do some minimal local testing before each commit:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

If you ever want to delete them you just have to do:

```bash
pre-commit clean
```
