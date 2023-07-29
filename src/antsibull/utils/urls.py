# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Utilities for working with ansible URLs
"""

from __future__ import annotations

from packaging.version import Version as PypiVer

from ..constants import (
    ANSIBLE_CORE_RAW_URL,
    ANSIBLE_DOCUMENTATION_MINIMUM,
    ANSIBLE_DOCUMENTATION_RANGES,
    ANSIBLE_DOCUMENTATION_RAW_URL,
)


def get_documentation_repo_raw_url(version: PypiVer) -> str:
    """
    Return the raw url for retrieving ansible documentation files
    See https://github.com/ansible-community/community-topics/issues/240.
    """
    major_minor = f"{version.major}.{version.minor}"
    minimum_version = ANSIBLE_DOCUMENTATION_RANGES.get(
        major_minor, ANSIBLE_DOCUMENTATION_MINIMUM
    )
    return (
        ANSIBLE_DOCUMENTATION_RAW_URL
        if version >= minimum_version
        else ANSIBLE_CORE_RAW_URL
    )
