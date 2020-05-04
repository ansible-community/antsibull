# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

import asyncio
import os

import aiohttp
import semantic_version as semver

from .ansible_base import AnsibleBasePyPiClient
from .dependency_files import BuildFile, parse_pieces_file
from .galaxy import GalaxyClient


def display_exception(loop, context):
    print(context.get('exception'))


async def get_version_info(collections):
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(display_exception)

    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        pypi_client = AnsibleBasePyPiClient(aio_session)
        requestors['_ansible_base'] = asyncio.create_task(pypi_client.get_versions())
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
