#!/bin/sh
set -e
poetry run python -m pytest --cov-branch --cov=antsibull --cov-report term-missing -vv tests "$@"
