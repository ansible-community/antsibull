# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import filecmp
from pathlib import Path

import pytest

from antsibull.cli.antsibull_build import run

ANNOUNCEMENT_TESTS = [
    ("7.4.0", "announce-7.4.0"),
]


@pytest.mark.parametrize("version, directory", ANNOUNCEMENT_TESTS)
def test_announcements_command(
    test_data_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    version: str,
    directory: str,
) -> None:
    result_path = tmp_path_factory.mktemp(f"announcements-{version}")
    ret = run(
        [
            "antsibull-build",
            "announcements",
            f"--data-dir={test_data_path}",
            f"-O{result_path}",
            version,
        ]
    )
    assert ret == 0
    expected = test_data_path / directory
    expected_files = set()
    for file in expected.iterdir():
        assert filecmp.cmp(file, result_path / file.name)
        expected_files.add(file.name)
    for file in result_path.iterdir():
        assert (
            file.name in expected_files
        ), f"{file.name} should not have been generated"
