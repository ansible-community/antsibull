# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

import asyncio
import os
from urllib.parse import urljoin

import aiohttp
import semantic_version as semver

from .dependency_files import BuildFile, parse_pieces_file
from .galaxy import GalaxyClient


PYPI_SERVER_URL = 'https://test.pypi.org/'


def display_exception(loop, context):
    print(context.get('exception'))


async def get_ansible_base_version(aio_session, pypi_server_url=PYPI_SERVER_URL):
    # Retrieve the ansible-base package info from pypi
    query_url = urljoin(pypi_server_url, 'pypi/ansible-base/json')
    async with aio_session.get(query_url) as response:
        pkg_info = await response.json()

    # Calculate the newest version of the package
    return [pkg_info['info']['version']]


async def get_version_info(collections):
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(display_exception)

    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        requestors['_ansible_base'] = asyncio.create_task(get_ansible_base_version(aio_session))
        galaxy_client = GalaxyClient(aio_session)

        for collection in collections:
            requestors[collection] = asyncio.create_task(
                galaxy_client.get_versions(collection))

        collection_versions = {}
        responses = await asyncio.gather(*requestors.values())

        for idx, collection_name in enumerate(requestors):
            collection_versions[collection_name] = responses[idx]

    return collection_versions


def version_is_compatible(ansible_base_version, collection, version):
    # Metadata for this is not currently implemented.  So everything is rated as compatible
    return True


def find_latest_compatible(ansible_base_version, raw_dependency_versions):
    # Note: ansible-base compatibility is not currently implemented.  It will be a piece of
    # collection metadata that is present in the collection but may not be present in galaxy.  We'll
    # have to figure that out once the pieces are finalized

    # Order versions
    reduced_versions = {}
    for dep, versions in raw_dependency_versions.items():
        # Order the versions
        versions = [semver.Version(v) for v in versions]
        versions.sort(reverse=True)

        # Step through the versions to select the latest one which is compatible
        for version in versions:
            if version_is_compatible(ansible_base_version, dep, version):
                reduced_versions[dep] = version
                break

    return reduced_versions


def new_acd_command(args):
    collections = parse_pieces_file(args.pieces_file)
    dependencies = asyncio.run(get_version_info(collections))

    ansible_base_version = dependencies.pop('_ansible_base')[0]
    dependencies = find_latest_compatible(ansible_base_version, dependencies)

    build_filename = os.path.join(args.dest_dir, args.build_file)
    build_file = BuildFile(build_filename)
    build_file.write(args.acd_version, ansible_base_version, dependencies)

    return 0
