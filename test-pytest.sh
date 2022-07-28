#!/bin/sh
# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

set -e
PYTHONPATH=src poetry run python -W 'ignore:"@coroutine" decorator is deprecated::asynctest.case' \
	-m pytest --cov-branch --cov=antsibull --cov-report term-missing -vv tests "$@"
