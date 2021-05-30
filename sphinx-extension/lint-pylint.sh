#!/bin/bash
set -e
poetry run pylint --rcfile ../.pylintrc.automated sphinx_antsibull_ext "$@"
