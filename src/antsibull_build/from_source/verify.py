# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Verify collection source trees
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Collection
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

import aiofiles.ospath
from antsibull_core import app_context
from antsibull_fileutils.hashing import verify_hash

from antsibull_build.types import add_yaml_type

if TYPE_CHECKING:
    from typing_extensions import NotRequired


class FileError(str, Enum):
    """
    Collections source verification errors
    """

    # A file exists in the repo but its hash is invalid
    WRONG_HASH = "WRONG_HASH"
    # A file does not exist in the repo
    MISSING_FILE = "MISSING_FILE"
    # A directory in the artifact is a regular file in the repo
    NOT_A_DIRECTORY = "NOT_A_DIRECTORY"
    # The collection namespace/name in galaxy.yml does not match
    WRONG_GALAXY_YML_NAME = "WRONG_GALAXY_YML_NAME"

    def __str__(self) -> str:
        return self.name


LENIENT_FILE_ERROR_IGNORES = frozenset({FileError.MISSING_FILE})


add_yaml_type(FileError)


class FileErrorOutput(TypedDict):
    """
    Mapping of a FileError and the file name
    """

    file: str
    error: FileError
    message: NotRequired[str]


async def verify_files(
    collection: str,  # pylint: disable=unused-argument
    collection_dir: Path,
    files_data: list[dict[str, Any]],
    ignore_errors: Collection[FileError] | None = None,
) -> AsyncIterator[FileErrorOutput]:
    """
    Ensure that files in a collection git repository checkout match the
    artifact's FILES.json metadata

    Args:
        collection:
            Name of the collection being tested
        checkout_dir:
            Directory containing a collection checkout
        files_data:
            The `files` list from a collection artifact's FILES.json metadata
        ignore_errors:
            Collection of `FileError`s to ignore to ignore.
            Defaults to `{MISSING_FILE}`.

    Yields:
        `FileErrorOutput` dicts with error data
    """
    lib_ctx = app_context.lib_ctx.get()
    for file in files_data:
        path = collection_dir / file["name"]
        is_dir = file["ftype"] == "dir"
        error: FileError | None = None
        if not await aiofiles.ospath.exists(path):
            error = FileError.MISSING_FILE
        elif is_dir and not await aiofiles.ospath.isdir(path):
            error = FileError.NOT_A_DIRECTORY
        elif not is_dir and not await verify_hash(
            path,
            file["chksum_sha256"],
            algorithm="sha256",
            chunksize=lib_ctx.chunksize,
        ):
            error = FileError.WRONG_HASH
        if error is not None and error not in (ignore_errors or set()):
            yield FileErrorOutput({"file": file["name"], "error": error})
