# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import filecmp
import subprocess
import sys
from pathlib import Path

import pytest

from antsibull_build.cli.antsibull_build import run

ANNOUNCEMENT_TESTS = [
    ("7.0.0b1", "announce-7.0.0b1"),
    ("7.0.0", "announce-7.0.0"),
    ("7.4.0", "announce-7.4.0"),
]

COLOR_BOLD = "\x1B[0;97m\x1B[1m"
COLOR_NORMAL = "\x1B[0m"


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
    failures = False
    for file in expected.iterdir():
        resulting_file = result_path / file.name
        if not resulting_file.exists():
            failures = True
            print(
                f"❌  {COLOR_BOLD}{file.name}{COLOR_NORMAL}: {resulting_file} does not exist",
                file=sys.stderr,
            )
        elif not filecmp.cmp(file, resulting_file):
            failures = True
            print(
                f"❌  {COLOR_BOLD}{file.name}{COLOR_NORMAL}: {resulting_file} differs from {file}",
                file=sys.stderr,
            )
            subprocess.call(
                ["diff", "--unified", "--color=always", str(file), str(resulting_file)]
            )
        expected_files.add(file.name)
    for file in result_path.iterdir():
        if file.name not in expected_files:
            failures = True
            print(
                f"❌  {COLOR_BOLD}{file.name}{COLOR_NORMAL} should not have been generated",
                file=sys.stderr,
            )

    if failures:
        print(
            "⚠️  If you updated the announcement messages and the tests are now failing, "
            f"you can run {COLOR_BOLD}cp {result_path}/* {expected}/{COLOR_NORMAL} to copy the generated files "
            "to the test fixtures. Then you can use `git diff` to see the differences.",
            file=sys.stderr,
        )

    assert not failures
