#!/bin/bash
set -e
MYPYPATH=stubs/ poetry run mypy src/antsibull sphinx_antsibull_ext "$@"
