# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

import pytest
from packaging.version import Version as PypiVer

from antsibull.constants import ANSIBLE_CORE_RAW_URL, ANSIBLE_DOCUMENTATION_RAW_URL
from antsibull.utils.urls import get_documentation_repo_raw_url


@pytest.mark.parametrize(
    "version, expected",
    [
        pytest.param(PypiVer("2.12.0"), ANSIBLE_CORE_RAW_URL),
        pytest.param(PypiVer("2.13.0"), ANSIBLE_CORE_RAW_URL),
        pytest.param(PypiVer("2.13.11"), ANSIBLE_DOCUMENTATION_RAW_URL),
        pytest.param(PypiVer("2.14.8"), ANSIBLE_DOCUMENTATION_RAW_URL),
        pytest.param(PypiVer("2.16.0a1"), ANSIBLE_DOCUMENTATION_RAW_URL),
    ],
)
def test_get_documentation_repo_raw_url(version: PypiVer, expected: str):
    assert get_documentation_repo_raw_url(version) == expected
