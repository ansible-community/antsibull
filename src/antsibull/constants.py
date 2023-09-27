# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Constants used throughout the antsibull codebase
"""

from __future__ import annotations

from packaging.version import Version as PypiVer

MINIMUM_ANSIBLE_VERSION = PypiVer("6.0.0")
MINIMUM_ANSIBLE_VERSIONS = {
    "PACKAGE_DATA_NEW_METHOD": PypiVer("8.0.0a1"),
    # Whether to store setuptools config in setup.cfg
    "BUILD_META_MAKER": PypiVer("9.0.0.dev0"),
}

DOCSITE_BASE_URL = "https://docs.ansible.com/ansible"
DOCSITE_COMMUNITY_URL = "https://docs.ansible.com/ansible/latest/community"

COLLECTION_EXCLUDE_DIRS = ("docs", "tests")

# First ansible-core version that has its documentation split out into
# ansible/ansible-documentation.
ANSIBLE_DOCUMENTATION_MINIMUM = PypiVer("2.15.2")
ANSIBLE_DOCUMENTATION_RANGES: dict[str, PypiVer] = {
    "2.13": PypiVer("2.13.11"),
    "2.14": PypiVer("2.14.8"),
}
ANSIBLE_DOCUMENTATION_RAW_URL = "https://github.com/ansible/ansible-documentation/raw"
ANSIBLE_CORE_RAW_URL = "https://github.com/ansible/ansible/raw"
