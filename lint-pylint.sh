#!/bin/bash
set -e
poetry run pylint --rcfile .pylintrc.automated ansibulled
