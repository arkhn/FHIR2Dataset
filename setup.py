import os
from subprocess import call  # nosec

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

with open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.md"), encoding="utf-8"
) as f:
    long_description = f.read()


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


class BuildCommand(build_py):
    def run(self):
        call(["npm", "install", "--prefix", "fhir2dataset/tools/metadata"])  # nosec
        build_py.run(self)


class SdistCommand(sdist):
    def run(self):
        call(["npm", "install", "--prefix", "fhir2dataset/tools/metadata"])  # nosec
        sdist.run(self)


requirements = read("requirements.txt").split()

setup(
    cmdclass={"build_py": BuildCommand, "sdist": SdistCommand},
    name="fhir2dataset",
    packages=find_packages(),
    include_package_data=True,
    version="0.1.6",
    license="Apache License 2.0",
    description="Transform FHIR to Dataset",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Arkhn's Data Team",
    author_email="data@arkhn.com",
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
