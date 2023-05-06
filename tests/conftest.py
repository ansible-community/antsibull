# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TEST_DATA = HERE / "test_data"


@pytest.fixture
def test_data_path() -> Path:
    return TEST_DATA
