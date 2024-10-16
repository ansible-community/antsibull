# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from antsibull_build._vendor.shutil import _should_symlink
from antsibull_build.utils.paths import atemp_or_dir, copytree_and_symlinks, temp_or_dir


@pytest.mark.asyncio
async def test_atemp_or_dir_new(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextlib.asynccontextmanager
    async def mock_cm() -> AsyncIterator[str]:
        yield "abc"

    monkeypatch.setattr("aiofiles.tempfile.TemporaryDirectory", mock_cm)
    async with atemp_or_dir() as temp:
        assert temp == Path("abc")


@pytest.mark.asyncio
async def test_atemp_or_dir(tmp_path: Path) -> None:
    async with atemp_or_dir(tmp_path) as temp:
        assert temp == tmp_path


def test_temp_or_dir_new(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tempfile.TemporaryDirectory", lambda: contextlib.nullcontext("abc")
    )
    with temp_or_dir() as temp:
        assert temp == Path("abc")


def test_temp_or_dir(tmp_path: Path) -> None:
    with temp_or_dir(tmp_path) as temp:
        assert temp == tmp_path


def test_temp_not_dir(tmp_path: Path) -> None:
    abc = str(tmp_path / "abc")
    with pytest.raises(ValueError, match=f"{abc} is not a directory!"):
        temp_or_dir(abc).__enter__()


def test_should_symlink_relative(tmp_path: Path) -> None:
    here = tmp_path / "src" / "123"
    here.mkdir(parents=True)
    (here.parent / "xyz").touch()
    (here / "test_dir").mkdir()
    assert not _should_symlink(here, Path("test_dir/../../"), here)
    assert _should_symlink(here, Path("test_dir/../../123"), here)


def test_should_symlink_absolute() -> None:
    # This should never be accessed if the symlink is absolute
    fake_path = MagicMock(side_effect=Exception)
    #
    assert _should_symlink(Path("src/abc"), Path("/bin/bash"), fake_path)


def test_should_symlink_simple(tmp_path: Path) -> None:
    here = tmp_path / "src" / "123"
    here.mkdir(parents=True)
    (here / "xyz").touch()
    assert _should_symlink(here, Path("xyz"), here)

    (here2 := here / "another_directory").mkdir()
    (here2 / "456").touch()
    assert _should_symlink(here, Path("another_directory/456"), here)


def _pathiter(directory: Path, /) -> Iterator[Path]:
    for path in directory.iterdir():
        if path.is_dir() and not path.is_symlink():
            yield path
            yield from _pathiter(path)
        else:
            yield path


def test_copytree_functional(
    tmp_path: Path, test_data_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old = test_data_path / "copytree"
    new = tmp_path / "newtree"
    copytree_and_symlinks(old, new)

    new_paths = list(_pathiter(new))
    assert len(new_paths) == 8
    monkeypatch.chdir(new)
    assert Path("a2").readlink() == Path("a")
    assert Path("recursive").readlink() == Path()
    assert Path("README.md").is_file() and not Path("README.md").is_symlink()
