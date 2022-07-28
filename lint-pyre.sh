#!/bin/bash
# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

PURELIB=$(poetry run python -c 'from distutils.sysconfig import get_python_lib;print(get_python_lib(0))')
PLATLIB=$(poetry run python -c 'from distutils.sysconfig import get_python_lib;print(get_python_lib(1))')
poetry run pyre --source-directory src --search-path ../antsibull-changelog/src/ --search-path ../antsibull-core/src/ --search-path ../antsibull-docs/src/ --search-path "$PURELIB" --search-path "$PLATLIB" --search-path stubs/ "$@"
