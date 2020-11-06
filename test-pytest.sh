#!/bin/sh
set -e
poetry run python -m pytest --cov-branch --cov=antsibull --cov=sphinx_antsibull_ext --cov-report term-missing -vv tests "$@"
