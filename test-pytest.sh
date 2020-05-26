#!/bin/sh
set -e
poetry run python -m pytest --cov-branch --cov=antsibull -vv tests "$@"
