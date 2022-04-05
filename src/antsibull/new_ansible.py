# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Build command for creating a new major Ansible version."""

import asyncio
import os

import aiohttp
import asyncio_pool
import semantic_version as semver

from antsibull_core import app_context
from antsibull_core.ansible_core import AnsibleCorePyPiClient
from antsibull_core.dependency_files import BuildFile, parse_pieces_file
from antsibull_core.galaxy import GalaxyClient

from .changelog import ChangelogData


def display_exception(loop, context):  # pylint:disable=unused-argument
    print(context.get('exception'))


async def get_version_info(collections, pypi_server_url):
    """
    Return the versions of all the collections and ansible-core
    """
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(display_exception)

    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        lib_ctx = app_context.lib_ctx.get()
        async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
            pypi_client = AnsibleCorePyPiClient(aio_session, pypi_server_url=pypi_server_url)
            requestors['_ansible_core'] = await pool.spawn(pypi_client.get_versions())
            galaxy_client = GalaxyClient(aio_session)

            for collection in collections:
                requestors[collection] = await pool.spawn(
                    galaxy_client.get_versions(collection))

            collection_versions = {}
            responses = await asyncio.gather(*requestors.values())

    for idx, collection_name in enumerate(requestors):
        collection_versions[collection_name] = responses[idx]

    return collection_versions


# pylint:disable-next=unused-argument
def version_is_compatible(ansible_core_version, collection: str, version: semver.Version,
                          allow_prereleases: bool = False):
    # Metadata for this is not currently implemented.  So everything is rated as compatible
    # as long as it is no prerelease
    if version.prerelease and not allow_prereleases:
        return False
    return True


def find_latest_compatible(ansible_core_version, raw_dependency_versions,
                           allow_prereleases: bool = False):
    # Note: ansible-core compatibility is not currently implemented.  It will be a piece of
    # collection metadata that is present in the collection but may not be present in galaxy.
    # We'll have to figure that out once the pieces are finalized

    # Order versions
    reduced_versions = {}
    for dep, versions in raw_dependency_versions.items():
        # Order the versions
        versions = [semver.Version(v) for v in versions]
        versions.sort(reverse=True)

        # Step through the versions to select the latest one which is compatible
        for version in versions:
            if version_is_compatible(ansible_core_version, dep, version,
                                     allow_prereleases=allow_prereleases):
                reduced_versions[dep] = version
                break

    return reduced_versions


def new_ansible_command():
    app_ctx = app_context.app_ctx.get()
    collections = parse_pieces_file(
        os.path.join(app_ctx.extra['data_dir'], app_ctx.extra['pieces_file']))
    dependencies = asyncio.run(get_version_info(collections, app_ctx.pypi_url))

    ansible_core_version = dependencies.pop('_ansible_core')[0]
    dependencies = find_latest_compatible(
        ansible_core_version, dependencies, allow_prereleases=app_ctx.extra['allow_prereleases'])

    build_filename = os.path.join(app_ctx.extra['dest_data_dir'], app_ctx.extra['build_file'])
    build_file = BuildFile(build_filename)
    build_file.write(app_ctx.extra['ansible_version'], ansible_core_version, dependencies)

    changelog = ChangelogData.ansible(app_ctx.extra['dest_data_dir'])
    changelog.changes.save()

    return 0
