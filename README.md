# FHIR2Dataset

Transform FHIR to dataset for ML applications

## FHIR2Dataset in Detail

This project is still under development.

This repo is a POC allowing to make a query (close to SQL format) on a FHIR API and to retrieve tabular data.

The request that FHIR2Dataset performs on a FHIR API is specified in a configuration file of this [form](examples/config_template.json).
The purpose of this file is to perform a query whose result will be identical to the next SQL query:

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

## Installation

After cloning this repository, you can install the required dependencies

```
pip install -r requirements.txt
```

For usage, refer to this [turorial](https://htmlpreview.github.io/?https://github.com/arkhn/FHIR2Dataset/blob/query_tests/examples/tutorial.html) and then this [Jupyer Notebook](examples/example.ipynb)

## Examples

Check out examples of queries and how they are transformed in call to the FHIR api!

- [Select the gender and name for patients born after 2000](examples/example1.md)
- [Get the pressure measures of patients born after 1970, together with their gender and birthdate](examples/example2.md)
- [Get the number of patients currently in intensive care unit because of Coronavirus](examples/example3.md)
- [Get clinical information about patients that were in intensive care unit because of Coronavirus](examples/example4.md)

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
