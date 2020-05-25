#!/bin/sh
set -e
poetry run python -m pytest --cov-branch --cov=ansibulled -vv tests "$@"
