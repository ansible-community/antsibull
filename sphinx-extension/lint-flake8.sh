#!/bin/bash
set -e
poetry run flake8 sphinx_antsibull_ext --count --max-complexity=10 --max-line-length=100 --statistics "$@"
