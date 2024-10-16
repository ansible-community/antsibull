# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Clone collection repos
"""

from __future__ import annotations

import asyncio
import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import aiofiles.os
import aiofiles.ospath
from antsibull_core.logging import log
from antsibull_core.subprocess_util import async_log_run
from antsibull_fileutils.yaml import load_yaml_file, store_yaml_file

from antsibull_build.tagging import CollectionTagData
from antsibull_build.types import CollectionName
from antsibull_build.utils.paths import copytree_and_symlinks

from .exceptions import CloneError
from .verify import FileError, FileErrorOutput

if TYPE_CHECKING:
    from _typeshed import StrPath

mlog = log.fields(mod=__name__)


async def clone_collection(
    collection: CollectionName,
    tag_data: CollectionTagData,
    download_dir: Path,
    *,
    depth: int | None = 1,
) -> Path:
    """
    Clone a collection's git repository

    Args:
        tag_data:
            A tag dictionary. See `antsibull_build.tagging.get_collections_tags()`.
    Returns:
        The path to the collection checkout
    """
    flog = mlog.fields(func="clone_collection")
    if not all((tag_data["repository"], tag_data["tag"])):
        raise CloneError(
            "'tag_data' does not specify a 'repository' and 'tag'", collection
        )
    dest = download_dir / collection.namespace / collection.name
    await asyncio.to_thread(dest.parent.mkdir, exist_ok=True)
    args: list[StrPath] = [
        "git",
        "clone",
        f"--branch={tag_data['tag']}",
        cast(str, tag_data["repository"]),
        dest,
    ]
    if depth is not None:
        args.insert(2, f"--depth={depth}")
    await async_log_run(args, logger=flog)
    return dest


@dataclasses.dataclass
class NormalizedCheckout:
    """
    Dataclass that represents a collection checkout

    Attributes:
        collection:
            The collection namespace/name
        clone_directory:
            Path to the collection's git checkout
        normalized_data:
            A normalized version of the galaxy.yml
        data_changed:
            Whether the metadata was modified during normalization
        collection_directory:
            Path to the collection directory with galaxy.yml.
            If not passed and clone_directory ends with
            `ansible_collections/NAMESPACE/NAME`, this is set to
            `clone_directory`.
    """

    collection: CollectionName
    tag_data: CollectionTagData
    clone_directory: Path
    normalized_data: dict[str, Any]
    data_changed: bool
    collection_directory: Path | None
    errors: list[FileErrorOutput] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        self.collection_directory = self._guess_collection_directory()

    @property
    def collection_subdir(self) -> Path:
        return Path(self.tag_data.get("collection_directory", "./"))

    def _guess_collection_directory(self) -> Path | None:
        if not self.collection_directory:
            collection_subdir = self.clone_directory / self.collection_subdir
            if _matches_collection(collection_subdir, self.collection):
                return collection_subdir
        else:
            _matches_collection_err(self.collection_directory, self.collection)
        return self.collection_directory

    async def add_to_collection_tree(
        self, tree_path: Path, allow_symlink: bool = True
    ) -> Path:
        dest = Path(tree_path, *self.collection.parts)
        _matches_collection_err(dest, self.collection)
        await asyncio.to_thread(dest.parent.mkdir, exist_ok=True)
        if self.collection_directory and allow_symlink:
            await aiofiles.os.symlink(self.collection_directory.absolute(), dest)
        else:
            await asyncio.to_thread(
                copytree_and_symlinks,
                self.clone_directory / self.collection_subdir,
                dest,
            )
        return dest


def _matches_collection(directory: Path, collection: CollectionName) -> bool:
    return directory.parts[-3:] == ("ansible_collections", *collection.parts)


def _matches_collection_err(directory: Path, collection: CollectionName) -> None:
    if not _matches_collection(directory, collection):
        msg = f"{directory!r} does not end in ansible_collections/NAMESPACE/NAME"
        raise ValueError(msg)


async def normalize_clone(
    collection: CollectionName,
    checkout_dir: Path,
    tag_data: CollectionTagData,
) -> NormalizedCheckout:
    """
    Normalize a collection checkout. Ensure that the collection namespace,
    name, and version in galaxy.yml are correct.

    Args:
        checkout_dir:
            Path to the collection git checkout
        expected_collection:
            Expected NAMESPACE.NAME of the collection
        tag_data:
            A tag dictionary. See `antsibull_build.tagging.get_collections_tags()`.
    """
    flog = mlog.fields(func="normalize_clone", collection=collection)
    errors: list[FileErrorOutput] = []

    collection_directory = checkout_dir / tag_data.get("collection_directory", "./")
    galaxy_path = collection_directory / "galaxy.yml"
    if not await aiofiles.ospath.isfile(galaxy_path):
        raise CloneError(f"{galaxy_path} does not exist!", collection)
    galaxy_data: dict[str, Any] = load_yaml_file(galaxy_path)
    new_data = galaxy_data.copy()

    gotten_collection = f"{galaxy_data.get('namespace')}.{galaxy_data.get('name')}"
    if gotten_collection != collection:
        new_data["namespace"], new_data["name"] = collection.parts
        msg = (
            "Divergent collection names found."
            f" expected collection is {collection!r}"
            f" and galaxy metadata says {gotten_collection!r}"
        )
        flog.warning(msg)
        errors.append(
            {
                "file": "galaxy.yml",
                "error": FileError.WRONG_GALAXY_YML_NAME,
                "message": f"`{gotten_collection}` != `{collection}`",
            }
        )

    # Some collections set version to nil and change it dynamically...
    # Others don't set version at all, hence the .get()
    if galaxy_data.get("version") is None:
        new_data["version"] = tag_data["version"]
    elif new_data["version"] != tag_data["version"]:
        new_data["version"] = tag_data["version"]
        msg = (
            "Divergent collection versions found."
            f" expected version is {tag_data['version']!r}"
            f" and galaxy metadata says {galaxy_data['version']!r}"
        )
        flog.warning(msg)

    if changed := galaxy_data != new_data:
        store_yaml_file(galaxy_path, new_data)
    return NormalizedCheckout(
        collection, tag_data, checkout_dir, new_data, changed, None, errors
    )


__all__ = ("clone_collection", "normalize_clone", "NormalizedCheckout")
