# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Utility functions for dealing with paths and directories
"""

from __future__ import annotations

import contextlib
import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles.ospath
import aiofiles.tempfile

from antsibull_build._vendor.shutil import copytree_and_symlinks

if TYPE_CHECKING:
    from _typeshed import StrPath


def _is_dir(directory: Path) -> None:
    if not directory.is_dir():
        raise ValueError(f"{directory} is not a directory!")


@contextlib.contextmanager
def temp_or_dir(directory: StrPath | None = None, /) -> Iterator[Path]:
    if directory:
        directory = Path(directory)
        _is_dir(directory)
        yield directory
    else:
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)


@contextlib.asynccontextmanager
async def atemp_or_dir(directory: StrPath | None = None, /) -> AsyncIterator[Path]:
    if directory:
        directory = Path(directory)
        _is_dir(directory)
        yield directory
    else:
        async with aiofiles.tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)


__all__ = ("temp_or_dir", "atemp_or_dir", "copytree_and_symlinks")
