#!/bin/bash
set -e
MYPYPATH=stubs/ poetry run mypy antsibull sphinx_antsibull_ext "$@"
