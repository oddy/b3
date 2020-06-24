
from setuptools import setup
import codecs
import os.path

here = os.path.abspath(os.path.dirname(__file__))

def read(rel_path):
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()

def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")

setup(
    name = "b3buf",
    version = get_version("b3/__init__.py"),
    packages = ["b3"],
    install_requires = ["six"],

    description = "B3 is a binary serializer which is easy like json, compact like msgpack, powerful like protobuf, and handles datetimes in python",
    long_description = open(os.path.join(here,"README.md"),"rb").read(),
    long_description_content_type = "text/markdown",

    url = "https://github.com/oddy/b3",
    author = "Beau Butler (Oddy)",
    author_email = "beau.butler@gmail.com",

    license = "MIT",
    classifiers = [
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],

    include_package_data = True,

    # we want a universal wheel
    options={  'bdist_wheel' : {'universal' : True}  },
)
