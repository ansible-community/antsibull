#!/bin/bash
set -e
poetry run pylint --rcfile .pylintrc.automated antsibull sphinx_antsibull_ext "$@"
