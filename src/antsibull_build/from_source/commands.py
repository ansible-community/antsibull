# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Commands to clone and verify collections from source
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Collection, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import asyncio_pool  # type: ignore[import]
from antsibull_core import app_context
from antsibull_core.subprocess_util import async_log_run
from antsibull_fileutils.yaml import load_yaml_file, store_yaml_file

from antsibull_build.build_ansible_commands import download_collections
from antsibull_build.tagging import CollectionTagData
from antsibull_build.types import CollectionName, make_collection_mapping
from antsibull_build.utils.galaxy import create_galaxy_context
from antsibull_build.utils.paths import atemp_or_dir

from ._utils import filter_tag_data, tag_data_as_version_mapping
from .clone import NormalizedCheckout, clone_collection, normalize_clone
from .verify import FileError, verify_files

if TYPE_CHECKING:
    from _typeshed import StrPath


async def _extract_files_data(collection: StrPath) -> list[dict[str, Any]]:
    data = (await async_log_run(["tar", "-Oxf", collection, "FILES.json"])).stdout
    return json.loads(data)["files"]


async def _clone_collections(
    collections: dict[CollectionName, CollectionTagData], download_dir: Path
) -> dict[CollectionName, Path]:
    for namespace in {col.namespace for col in collections}:
        (download_dir / namespace).mkdir()
    lib_ctx = app_context.lib_ctx.get()
    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        requestors = {
            collection: await pool.spawn(
                clone_collection(collection, data, download_dir)
            )
            for collection, data in collections.items()
        }
        values = await asyncio.gather(*requestors.values())
    final: dict[CollectionName, Path] = dict(zip(collections.keys(), values))
    return final


async def _handle_collection(
    collection: CollectionName,
    tag_data: CollectionTagData,
    artifact: Path,
    checkout: Path,
    ignore_errors: Collection[FileError] | None,
) -> NormalizedCheckout:
    norm = await normalize_clone(collection, checkout, tag_data)
    norm.errors.extend(
        [
            output
            async for output in verify_files(
                collection,
                checkout / norm.collection_subdir,
                (await _extract_files_data(artifact)),
                ignore_errors,
            )
        ]
    )
    return norm


async def _handle_collections(
    tag_data: dict[CollectionName, CollectionTagData],
    artifacts: dict[CollectionName, str],
    checkouts: dict[CollectionName, Path],
    ignore_errors: Collection[FileError] | None,
) -> list[NormalizedCheckout]:
    lib_ctx = app_context.lib_ctx.get()
    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        tasks = [
            await pool.spawn(
                _handle_collection(
                    collection,
                    tag_data[collection],
                    Path(artifacts[collection]),
                    checkouts[collection],
                    ignore_errors,
                )
            )
            for collection in tag_data
        ]
        return list(await asyncio.gather(*tasks))


async def _symlink_tree(
    checkouts: Iterable[NormalizedCheckout], tree_path: Path, allow_symlink: bool = True
):
    lib_ctx = app_context.lib_ctx.get()
    for namespace in {col.collection.namespace for col in checkouts}:
        (tree_path / namespace).mkdir()
    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        tasks = [
            await pool.spawn(
                collection.add_to_collection_tree(tree_path, allow_symlink)
            )
            for collection in checkouts
        ]
        await asyncio.gather(*tasks)


#####


def verify_upstream_command() -> int:
    """
    Ensure that files in a collection's git repository (roughly) match the
    contents of its upstream repository
    """
    return asyncio.run(_verify_upstream_command())


async def _verify_upstream_command() -> int:
    app_ctx = app_context.app_ctx.get()
    lib_ctx = app_context.lib_ctx.get()
    tags_file: Path = app_ctx.extra["tags_file"]
    globs: list[str] | None = app_ctx.extra["globs"]
    download_dir: Path | None = app_ctx.extra["download_dir"]
    checkouts_dir_: Path | None = app_ctx.extra["checkouts_dir"]
    tree_dir: Path | None = app_ctx.extra["tree_dir"]
    ignores: Collection[FileError] = app_ctx.extra["ignores"]
    error_output: Path = app_ctx.extra["error_output"]

    tags_data: dict[CollectionName, CollectionTagData] = make_collection_mapping(
        load_yaml_file(tags_file)
    )
    tags_data = filter_tag_data(tags_data, globs)
    versions = tag_data_as_version_mapping(tags_data)
    async with atemp_or_dir(download_dir) as download_dir:
        artifacts_dir = download_dir / "collection_artifacts"
        artifacts_dir.mkdir(parents=True)
        checkouts_dir = Path(
            (checkouts_dir_ or (download_dir / "checkouts")),
            "ansible_collections",
        )
        checkouts_dir.mkdir(parents=True)
        if tree_dir:
            tree_dir /= "ansible_collections"
            tree_dir.mkdir(parents=True)

        artifacts = make_collection_mapping(
            await download_collections(
                versions,  # type: ignore[arg-type]
                str(artifacts_dir),
                await create_galaxy_context(),
                lib_ctx.collection_cache,
            )
        )
        checkouts = await _clone_collections(tags_data, checkouts_dir)

        normed_collections = await _handle_collections(
            tags_data, artifacts, checkouts, ignores
        )
        error_blob = {
            "collections": {
                coll.collection: coll.errors
                for coll in normed_collections
                if coll.errors
            }
        }

        store_yaml_file(error_output, error_blob)

        if tree_dir:
            # Create symlinks to collections in checkouts_dir instead of
            # copying if checkouts_dir is explicitly passed by the user as
            # opposed to being a temporary download directory.
            allow_symlink = bool(checkouts_dir_)
            #
            await _symlink_tree(normed_collections, tree_dir, allow_symlink)
    return bool(error_blob)


__all__ = ("verify_upstream_command",)
