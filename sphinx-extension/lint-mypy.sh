#!/bin/bash
set -e
MYPYPATH=stubs/ poetry run mypy sphinx_antsibull_ext "$@"
