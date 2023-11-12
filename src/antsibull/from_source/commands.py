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
from collections.abc import AsyncIterator, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiofiles
import aiofiles.os
import aiofiles.ospath
import asyncio_pool  # type: ignore[import]
from antsibull_core import app_context
from antsibull_core.subprocess_util import async_log_run
from antsibull_core.utils.hashing import verify_hash
from antsibull_core.yaml import _SafeDumper, load_yaml_file
from yaml import dump as dump_yaml_str

from antsibull.build_ansible_commands import download_collections
from antsibull.tagging import CollectionTagData
from antsibull.types import CollectionName, make_collection_mapping
from antsibull.utils.galaxy import create_galaxy_context
from antsibull.utils.paths import atemp_or_dir

from ._utils import filter_tag_data, tag_data_as_version_mapping
from .clone import NormalizedCheckout, clone_collection, normalize_clone

if TYPE_CHECKING:
    from _typeshed import StrPath


async def verify_files(
    collection: str,
    collection_dir: Path,
    files_data: list[dict[str, Any]],
    allow_missing=True,
) -> AsyncIterator[str]:
    """
    Ensure that files in a collection git repository checkout match the
    artifact's FILES.json metadata

    Args:
        checkout_dir:
            Directory containing a collection checkout
        files_data:
            The `files` list from a collection artifact's FILES.json metadata
        allow_missing:
            Whether to allow files in the collection artifact that are missing
            from FILES.json.
            We'd prefer that they didn't, but some collections may include
            generated files in collection artifacts, so this is allowed for now.

    Yields:
        Files whose checksums diverge between the checkout_dir and FILES.json metadata
    """
    del collection  # Not used for now. This shuts up the linter.
    for file in files_data:
        path = collection_dir / file["name"]
        is_dir = file["ftype"] == "dir"
        okay: bool = True
        if not await aiofiles.ospath.exists(path):
            okay = allow_missing
        elif is_dir:
            okay = await aiofiles.ospath.isdir(path)
        else:
            okay = await verify_hash(path, file["chksum_sha256"], "sha256")
        if not okay:
            yield file["name"]


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
    allow_missing: bool,
) -> NormalizedCheckout:
    norm = await normalize_clone(collection, checkout, tag_data)
    missing_files = [
        f
        async for f in verify_files(
            collection,
            checkout / norm.collection_subdir,
            (await _extract_files_data(artifact)),
            allow_missing=allow_missing,
        )
    ]
    norm.errors.extend([f"{f} does not match" for f in missing_files])
    return norm


async def _handle_collections(
    tag_data: dict[CollectionName, CollectionTagData],
    artifacts: dict[CollectionName, str],
    checkouts: dict[CollectionName, Path],
    allow_missing: bool = True,
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
                    allow_missing,
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
    tags_data: dict[CollectionName, CollectionTagData] = make_collection_mapping(
        load_yaml_file(app_ctx.extra["tags_file"])
    )
    tags_data = filter_tag_data(tags_data, app_ctx.extra["globs"])
    versions = tag_data_as_version_mapping(tags_data)
    async with atemp_or_dir(app_ctx.extra["download_dir"]) as download_dir:
        artifacts_dir = download_dir / "collection_artifacts"
        artifacts_dir.mkdir(parents=True)
        checkouts_dir = Path(
            (app_ctx.extra["checkouts_dir"] or (download_dir / "checkouts")),
            "ansible_collections",
        )
        checkouts_dir.mkdir(parents=True)
        tree_dir: Path | None = app_ctx.extra["tree_dir"]
        if tree_dir:
            tree_dir /= "ansible_collections"
            tree_dir.mkdir(parents=True)

        artifacts = make_collection_mapping(
            await download_collections(
                versions,  # type: ignore[arg-type]
                str(artifacts_dir),
                await create_galaxy_context(),
                app_ctx.collection_cache,
            )
        )
        checkouts = await _clone_collections(tags_data, checkouts_dir)

        normed_collections = await _handle_collections(
            tags_data, artifacts, checkouts, app_ctx.extra["allow_missing"]
        )
        error_blob = {
            "collections": {
                coll.collection: coll.errors
                for coll in normed_collections
                if coll.errors
            }
        }

        error_yaml = dump_yaml_str(error_blob, Dumper=_SafeDumper)
        if app_ctx.extra["print_errors"]:
            print(error_yaml)
        error_output: Path | None = app_ctx.extra["error_output"]
        if error_output:
            error_output.write_text(error_yaml, "utf-8")

        if tree_dir:
            # Create symlinks to collections in checkouts_dir instead of
            # copying if checkouts_dir is explicitly passed by the user as
            # opposed to being a temporary download directory.
            allow_symlink = bool(app_ctx.extra["checkouts_dir"])
            #
            await _symlink_tree(normed_collections, tree_dir, allow_symlink)
    return bool(error_blob)


__all__ = ("verify_upstream_command",)
