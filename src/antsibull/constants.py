# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Constants used throughout the antsibull codebase
"""

from __future__ import annotations

from packaging.version import Version as PypiVer

MINIMUM_ANSIBLE_VERSION = PypiVer('6.0.0')
