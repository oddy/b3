
from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name = "b3buf",
    version = "0.9.0",
    packages = ["b3"],
    install_requires = ["six"],

    description = "B3 is a binary serializer which is easy like json, compact like msgpack, powerful like protobuf, and handles datetimes in python",
    long_description = open("README.md").read(),
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
