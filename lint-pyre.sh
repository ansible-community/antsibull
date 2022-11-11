#!/bin/bash
# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

set -e

PURELIB=$(poetry run python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
PLATLIB=$(poetry run python -c 'import sysconfig; print(sysconfig.get_path("platlib"))')
poetry run pyre --source-directory src --search-path ../antsibull-changelog/src/ --search-path ../antsibull-core/src/ --search-path ../antsibull-docs/src/ --search-path "$PURELIB" --search-path "$PLATLIB" --search-path stubs/ "$@"
