#!/usr/bin/env python3

import os
import setuptools

def readme():
  with open('README.md') as f:
    return f.read()

""" Only install within a virtualenv or conda environment """
def check_env():
  if os.getenv("VIRTUAL_ENV"):
    print("Installing in virtualenv: %s" % os.getenv("VIRTUAL_ENV")) 
    return  
  if os.getenv("CONDA_DEFAULT"):
    print("Installing in conda env: %s" % os.getenv("CONDA_DEFAULT"))
    return
  raise EnvironmentError("Not in a virtualenv or conda environment, aborting installation")
check_env()

setuptools.setup(name='simim',
  version='1.0.0',
  description='NISMOD spatial interaction models of internal migration',
  long_description=readme(),
  long_description_content_type="text/markdown",
  url='https://github.com/nismod/simim',
  author='Andrew P Smith',
  author_email='a.p.smith@leeds.ac.uk',
  packages=setuptools.find_packages(),
  install_requires=['numpy',
                    'pandas',
                    'geopandas',
                    'scipy',
                    'spint',
                    'ukpopulation',
                    # for visualisation:
                    'matplotlib',
                    'descartes'],
  classifiers=(
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
  ),
  #scripts=['scripts/run.py'],
  test_suite='nose.collector',
  tests_require=['nose'],
)
