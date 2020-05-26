#!/bin/bash
set -e
poetry run pyre --source-directory antsibull --search-path $(poetry run python -c 'from distutils.sysconfig import get_python_lib;print(get_python_lib())') --search-path stubs/ --search-path . "$@"
