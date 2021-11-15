#!/bin/sh
set -e
PYTHONPATH=src poetry run python -W 'ignore:"@coroutine" decorator is deprecated::asynctest.case' \
	-m pytest --cov-branch --cov=antsibull --cov=sphinx_antsibull_ext --cov-report term-missing -vv tests "$@"
