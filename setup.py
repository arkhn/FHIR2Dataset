import os
from setuptools import setup, find_packages

with open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.md"), encoding="utf-8",
) as f:
    long_description = f.read()


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


requirements = read("requirements.txt").split()

setup(
    name="fhir2dataset",
    packages=find_packages(),
    include_package_data=True,
    version="0.0.1",
    license="Apache License 2.0",
    description="Transform FHIR to Dataset",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Lucile Saulnier",
    author_email="contact@arkhn.com",
    url="https://github.com/arkhn/FHIR2Dataset",
    keywords=[
        "arkhn",
        "medical",
        "fhir"
    ],
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
