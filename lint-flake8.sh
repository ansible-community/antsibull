#!/bin/bash
# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

set -e
poetry run flake8 src/antsibull --count --max-complexity=10 --max-line-length=100 --statistics "$@"
