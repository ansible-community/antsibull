#!/bin/sh
set -e
poetry run python -W 'ignore:"@coroutine" decorator is deprecated::asynctest.case' \
	-m pytest --cov-branch --cov=sphinx_antsibull_ext --cov-report term-missing -vv tests "$@"
