# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

# It doesn't make sense to split up the long URLs
# flake8: noqa E501

import pytest
from packaging.version import Version as PypiVer

from antsibull.changelog import get_core_porting_guide_url


@pytest.mark.parametrize(
    "version, expected",
    [
        pytest.param(
            PypiVer("2.12.0"),
            "https://github.com/ansible/ansible/raw/v2.12.0/docs/docsite/rst/porting_guides/porting_guide_core_2.12.rst",
        ),
        pytest.param(
            PypiVer("2.13.0"),
            "https://github.com/ansible/ansible/raw/v2.13.0/docs/docsite/rst/porting_guides/porting_guide_core_2.13.rst",
        ),
        pytest.param(
            PypiVer("2.13.11"),
            "https://github.com/ansible/ansible-documentation/raw/v2.13.11/docs/docsite/rst/porting_guides/porting_guide_core_2.13.rst",
        ),
        pytest.param(
            PypiVer("2.14.8"),
            "https://github.com/ansible/ansible-documentation/raw/v2.14.8/docs/docsite/rst/porting_guides/porting_guide_core_2.14.rst",
        ),
        pytest.param(
            PypiVer("2.16.0a1"),
            "https://github.com/ansible/ansible-documentation/raw/v2.16.0a1/docs/docsite/rst/porting_guides/porting_guide_core_2.16.rst",
        ),
    ],
)
def test_get_core_porting_guide_url(version: PypiVer, expected: str):
    assert get_core_porting_guide_url(version) == expected
