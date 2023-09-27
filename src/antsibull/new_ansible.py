# Author: Toshio Kuratomi <tkuratom@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020
"""Build command for creating a new major Ansible version."""

from __future__ import annotations

import asyncio
import os
import typing as t
from collections.abc import Mapping, Sequence

import aiohttp
import asyncio_pool  # type: ignore[import]
import semantic_version as semver
from antsibull_core import app_context
from antsibull_core.ansible_core import AnsibleCorePyPiClient
from antsibull_core.dependency_files import BuildFile, parse_pieces_file
from antsibull_core.galaxy import GalaxyClient
from packaging.version import Version as PypiVer

from .changelog import ChangelogData
from .versions import load_constraints_if_exists


def display_exception(loop, context):  # pylint:disable=unused-argument
    print(context.get("exception"))


async def get_version_info(
    collections: Sequence[str], pypi_server_url: str
) -> tuple[dict[str, t.Any], dict[str, list[str]]]:
    """
    Return the versions of all the collections and ansible-core
    """
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(display_exception)

    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        lib_ctx = app_context.lib_ctx.get()
        async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
            pypi_client = AnsibleCorePyPiClient(
                aio_session, pypi_server_url=pypi_server_url
            )
            requestors["_ansible_core"] = await pool.spawn(
                pypi_client.get_release_info()
            )
            galaxy_client = GalaxyClient(aio_session)

            for collection in collections:
                requestors[collection] = await pool.spawn(
                    galaxy_client.get_versions(collection)
                )

            collection_versions = {}
            responses = await asyncio.gather(*requestors.values())

    ansible_core_release_infos: dict[str, t.Any] | None = None
    for idx, collection_name in enumerate(requestors):
        if collection_name == "_ansible_core":
            ansible_core_release_infos = responses[idx]
        else:
            collection_versions[collection_name] = responses[idx]

    if ansible_core_release_infos is None:
        raise RuntimeError("Internal error")

    return ansible_core_release_infos, collection_versions


def version_is_compatible(
    # pylint:disable-next=unused-argument
    ansible_core_version: PypiVer,
    # pylint:disable-next=unused-argument
    collection: str,
    version: semver.Version,
    allow_prereleases: bool = False,
    constraint: semver.SimpleSpec | None = None,
) -> bool:
    # Metadata for this is not currently implemented.  So everything is rated as compatible
    # as long as it is no prerelease
    if version.prerelease and not allow_prereleases:
        return False
    if constraint is not None and version not in constraint:
        return False
    return True


def find_latest_compatible(
    ansible_core_version: PypiVer,
    raw_dependency_versions: Mapping[str, Sequence[str]],
    allow_prereleases: bool = False,
    constraints: Mapping[str, semver.SimpleSpec] | None = None,
) -> dict[str, semver.Version]:
    # Note: ansible-core compatibility is not currently implemented.  It will be a piece of
    # collection metadata that is present in the collection but may not be present in galaxy.
    # We'll have to figure that out once the pieces are finalized

    constraints = constraints or {}

    # Order versions
    reduced_versions = {}
    for dep, versions in raw_dependency_versions.items():
        # Order the versions
        versions = [semver.Version(v) for v in versions]
        versions.sort(reverse=True)

        # Step through the versions to select the latest one which is compatible
        for version in versions:
            if version_is_compatible(
                ansible_core_version,
                dep,
                version,
                allow_prereleases=allow_prereleases,
                constraint=constraints.get(dep),
            ):
                reduced_versions[dep] = version
                break

        if dep not in reduced_versions:
            raise ValueError(f"Cannot find matching version for {dep}")

    return reduced_versions


def new_ansible_command() -> int:
    app_ctx = app_context.app_ctx.get()
    collections = parse_pieces_file(
        os.path.join(app_ctx.extra["data_dir"], app_ctx.extra["pieces_file"])
    )
    ansible_core_release_infos, dependencies = asyncio.run(
        get_version_info(collections, app_ctx.pypi_url)
    )
    ansible_core_versions = [
        (PypiVer(version), data[0]["requires_python"])
        for version, data in ansible_core_release_infos.items()
    ]
    ansible_core_versions.sort(reverse=True, key=lambda ver_req: ver_req[0])

    constraints_filename = os.path.join(
        app_ctx.extra["data_dir"], app_ctx.extra["constraints_file"]
    )
    constraints = load_constraints_if_exists(constraints_filename)

    ansible_core_version, python_requires = ansible_core_versions[0]
    dependencies = find_latest_compatible(
        ansible_core_version,
        dependencies,
        allow_prereleases=app_ctx.extra["allow_prereleases"],
        constraints=constraints,
    )

    build_filename = os.path.join(
        app_ctx.extra["dest_data_dir"], app_ctx.extra["build_file"]
    )
    build_file = BuildFile(build_filename)
    build_file.write(
        app_ctx.extra["ansible_version"],
        str(ansible_core_version),
        dependencies,
        python_requires=python_requires,
    )

    changelog = ChangelogData.ansible(app_ctx.extra["dest_data_dir"])
    changelog.changes.save()

    return 0
