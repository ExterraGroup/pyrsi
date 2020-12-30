#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    "cachetools",
    "requests",
    "fuzzywuzzy",
    "python-Levenshtein",
    "beautifulsoup4",
    "configparser"
]

setup_requirements = [ ]

test_requirements = [ ]

setup(
    author="Ventorvar",
    author_email='ventorvar@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Python API for interacting with the Roberts Space Industries site for Star Citizen.",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='pyrsi',
    name='pyrsi',
    packages=find_packages(include=['rsi']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://gitlab.com/scmodding/frameworks/pyrsi',
    version='0.1.16',
    zip_safe=True,
)
