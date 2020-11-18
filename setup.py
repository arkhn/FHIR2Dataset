import os
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

from subprocess import call

with open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.md"), encoding="utf-8"
) as f:
    long_description = f.read()


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


class MyBuildCommand(build_py):
    def run(self):
        call(["npm", "install", "--prefix", "fhir2dataset/metadata"])
        build_py.run(self)


class MySdistCommand(sdist):
    def run(self):
        call(["npm", "install", "--prefix", "fhir2dataset/metadata"])
        sdist.run(self)


requirements = read("requirements.txt").split()

setup(
    cmdclass={"build_py": MyBuildCommand, "sdist": MySdistCommand},
    name="fhir2dataset",
    packages=find_packages(),
    include_package_data=True,
    version="0.1.4",
    license="Apache License 2.0",
    description="Transform FHIR to Dataset",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Lucile Saulnier",
    author_email="contact@arkhn.com",
    url="https://github.com/arkhn/FHIR2Dataset",
    keywords=["arkhn", "medical", "fhir", "FHIR", "Dataset", "API"],
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
