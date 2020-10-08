# FHIR Query

Query any FHIR api using SQL.

## Usage

```python
import fhir2dataset as query
sql_query = "SELECT p.name.family, p.address.city FROM Patient AS p WHERE p.birthdate=1944 AND p.gender = 'female'"
query.sql(sql_query)
```
```
100%|██████████| 1000/1000 [00:01<00:00, 162.94it/s]

    p.name.family             p.address.city
--------------------------------------------
0   [Hegmann834, Schumm995]   [Los Angeles]
1   [Wilderman619, Wolff180]  [Chicago]
2   [Smid, Smid]              [Paris]
...
```

FHIR Query is still under active development, feedback and contributions are welcome!

## Installation

`pip install fhir2dataset`

### From source

After cloning this repository, you can install the required dependencies

```bash
pip install -r requirements.txt
npm install --prefix ./fhir2dataset/metadata
```

## Getting started

There are two possible ways to enter the query: as a SQL query or as a JSON config file

**SQL query**

You can define SQL queries of the following form:
```sql
sql_query = """
SELECT (alias n°1).a, (alias n°1).b, (alias n°2).a 
FROM (Resource type 1) as (alias n°1)
INNER JOIN (Resource type 2) as (alias n°2) ON (alias n°1).d = (alias n°2)
WHERE (alias n°2).c = "value 1"
AND (alias n°2).d = "value 2"
"""
```
Note that we only support a subset of SQL keywords.

By default, FHIR Query will use the HAPI FHIR Api. But you can use your own api using the following syntax:

```python
import fhir2dataset as query

fhir_api_url = 'https://api.awesome.fhir.org/baseR4/'
query.sql(sql_query, fhir_api_url=fhir_api_url)
```

**JSON config file**

You can also use JSON configuration files

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

```python
# Enter in dirname the path of config.json
filename_config = 'config.json'

with open(os.path.join(dirname, filename_config)) as json_file:
    config = json.load(json_file)

query.from_config(config)
query.execute()
df = query.main_dataframe
```

For extended usage, you can refer to this [tutorial](https://htmlpreview.github.io/?https://github.com/arkhn/FHIR2Dataset/blob/query_tests/examples/tutorial.html) and then this [Jupyter Notebook](examples/example.ipynb)


### More Examples

Check out examples of queries and how they are transformed in call to the FHIR api!

-   [Select the gender and name for patients born after 2000](examples/example1.md)
-   [Get clinical information about patients that were in intensive care unit because of Coronavirus](examples/example2.md)

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
