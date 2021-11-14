#!/bin/bash
set -e

PURELIB=$(poetry run python -c 'from distutils.sysconfig import get_python_lib;print(get_python_lib(0))')
PLATLIB=$(poetry run python -c 'from distutils.sysconfig import get_python_lib;print(get_python_lib(1))')
poetry run pyre --source-directory src --search-path "$PURELIB" --search-path "$PLATLIB" --search-path stubs/ "$@"
