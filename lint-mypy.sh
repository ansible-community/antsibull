#!/bin/bash
set -e
MYPYPATH=stubs/ poetry run mypy src/antsibull src/sphinx_antsibull_ext "$@"
