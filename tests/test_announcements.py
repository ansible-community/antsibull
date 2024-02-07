# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import filecmp
from pathlib import Path

from antsibull.cli.antsibull_build import run


def test_announcements_command(test_data_path: Path, tmp_path: Path) -> None:
    ret = run(
        [
            "antsibull-build",
            "announcements",
            f"--data-dir={test_data_path}",
            f"-O{tmp_path}",
            "7.4.0",
        ]
    )
    assert ret == 0
    expected = test_data_path / "announce-7.4.0"
    for file in expected.iterdir():
        assert filecmp.cmp(file, tmp_path / file.name)
