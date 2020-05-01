#!/bin/sh

args=${1-tests}
python3.8 -m pytest --cov-branch --cov=ansibulled $args -vv
