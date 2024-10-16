# Copyright (C) 2023 Felix Fontein <felix@fontein.de>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

import pytest

from antsibull_build.build_ansible_commands import feature_freeze_version


@pytest.mark.parametrize(
    "spec, expected",
    [
        pytest.param(
            ">=1.0.0,<2.0.0",
            ">=1.0.0,<1.1.0",
            id="simple",
        ),
        pytest.param(
            "<2.0.0,>=1.0.0",
            ">=1.0.0,<1.1.0",
            id="reverted-order",
        ),
        pytest.param(
            ">=1.2.3,<1.2.7",
            ">=1.2.3,<1.2.7",
            id="tiny interval",
        ),
        pytest.param(
            ">=1.2.3,<=1.2.7",
            ">=1.2.3,<=1.2.7",
            id="tiny interval",
        ),
        pytest.param(
            ">=1.2.3,<1.3.0",
            ">=1.2.3,<1.3.0",
            id="minor half-open interval",
        ),
        pytest.param(
            ">=1.2.3,<=1.3.0",
            ">=1.2.3,<1.3.0",
            id="minor closed interval",
        ),
        pytest.param(
            "==1.2.3",
            "==1.2.3",
            id="pinned version",
        ),
        pytest.param(
            ">=1.0.0,!=1.0.1,!=1.1.2,!=1.1.0,<2.0.0",
            "!=1.0.1,>=1.0.0,<1.1.0",
            id="exclusions",
        ),
    ],
)
def test_feature_freeze_version(
    spec: str,
    expected: str,
):
    result = feature_freeze_version(spec, "foo.bar")
    assert result == expected


@pytest.mark.parametrize(
    "spec, expected",
    [
        pytest.param(
            ">=1.0.0",
            "No upper version limit specified for foo.bar: >=1.0.0",
            id="no upper limit",
        ),
        pytest.param(
            ">1.0.0",
            "Strict lower bound specified for foo.bar: >1.0.0",
            id="strict lower bound",
        ),
        pytest.param(
            ">=0.1.0,<=1.0.0,<2.0.0",
            "Multiple upper version limits specified for foo.bar: >=0.1.0,<=1.0.0,<2.0.0",
            id="multiple upper versions",
        ),
        pytest.param(
            "<1.0.0",
            "No minimum version specified for foo.bar: <1.0.0",
            id="no minimum",
        ),
        pytest.param(
            ">=1.0.0,>=2.0.0",
            "Multiple minimum versions specified for foo.bar: >=1.0.0,>=2.0.0",
            id="multiple minimum versions",
        ),
        pytest.param(
            "==1.0.0,<2.0.0",
            "Pin combined with other clauses for foo.bar: ==1.0.0,<2.0.0",
            id="pin combined with others",
        ),
    ],
)
def test_feature_freeze_version_fail(
    spec: str,
    expected: str,
):
    with pytest.raises(ValueError) as exc_info:
        result = feature_freeze_version(spec, "foo.bar")
    assert exc_info.value.args[0] == expected
