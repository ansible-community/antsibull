#!/usr/bin/python3 -tt
# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020


import argparse
import asyncio
import json
import os
import os.path
import pkgutil
import shutil
import tempfile
from urllib.parse import urljoin

import aiohttp
import semantic_version as semver
import sh
from jinja2 import Template

from .dependency_files import BuildFile, DepsFile, parse_pieces_file
from .galaxy import CollectionDownloader, GalaxyClient


DEFAULT_FILE_BASE = 'acd'
DEFAULT_PIECES_FILE = f'{DEFAULT_FILE_BASE}.in'

PYPI_SERVER_URL = 'https://test.pypi.org/'
GALAXY_SERVER_URL = 'https://galaxy.ansible.com/'


class InvalidArgumentError(Exception):
    pass


def parse_args(program_name, args):
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('acd_version', type=semver.Version,
                               help='The X.Y.Z version of ACD that this will be for')
    common_parser.add_argument('--dest-dir', default='.',
                               help='Directory to write the output to')

    build_parser = argparse.ArgumentParser(add_help=False)
    build_parser.add_argument('--build-file', default=None,
                              help='File containing the list of collections with version ranges')
    build_parser.add_argument('--deps-file', default=None,
                              help='File which will be written containing the list of collections'
                              ' at versions which were included in this version of ACD')

    parser = argparse.ArgumentParser(prog=program_name,
                                     description='Script to manage building ACD')
    subparsers = parser.add_subparsers(title='Subcommands', dest='command',
                                       help='for help use build-acd.py SUBCOMMANDS -h')

    new_parser = subparsers.add_parser('new-acd', parents=[common_parser],
                                       description='Generate a new build description from the'
                                       ' latest available versions of ansible-base and the'
                                       ' included collections')
    new_parser.add_argument('--pieces-file', default=None,
                            help='File containing a list of collections to include')
    new_parser.add_argument('--build-file', default=None,
                            help='File which will be written which contains the list'
                            ' of collections with version ranges')

    subparsers.add_parser('build-single',
                          parents=[common_parser, build_parser],
                          description='Build a single-file ACD')

    subparsers.add_parser('build-multiple',
                          parents=[common_parser, build_parser],
                          description='Build a multi-file ACD')

    collection_parser = subparsers.add_parser('build-collection',
                                              parents=[common_parser],
                                              description='Build a collection which will'
                                              ' install ACD')
    collection_parser.add_argument('--deps-file', default=None,
                                   help='File which contains the list of collections and'
                                   ' versions which were included in this version of ACD')

    args = parser.parse_args(args)

    #
    # Validation and coercion
    #
    if args.command is None:
        raise InvalidArgumentError('Please specify a subcommand to run')

    if not os.path.isdir(args.dest_dir):
        raise InvalidArgumentError(f'{args.dest_dir} must be an existing directory')

    if args.command == 'new-acd':
        if args.pieces_file is not None:
            if not os.path.isfile(args.pieces_file):
                raise InvalidArgumentError(f'The pieces file, {args.pieces_file} must already'
                                           ' exist. It should contains one namespace.collection'
                                           ' per line')

        if args.build_file is None:
            basename = os.path.basename(os.path.splitext(args.pieces_file)[0])
            args.build_file = f'{basename}-{args.acd_version.major}.{args.acd_version.minor}.build'

    if args.command in ('build-single', 'build-multiple'):
        if args.build_file is None:
            args.build_file = (DEFAULT_FILE_BASE
                               + f'-{args.acd_version.major}.{args.acd_version.minor}.build')

        if not os.path.isfile(args.build_file):
            raise InvalidArgumentError(f'The build file, {args.build_file} must already exist.'
                                       ' It should contains one namespace.collection per line')

        if args.deps_file is None:
            major_minor = f'-{args.acd_version.major}.{args.acd_version.minor}'
            basename = os.path.basename(os.path.splitext(args.build_file)[0])
            if basename.endswith(major_minor):
                basename = basename[:-len(major_minor)]

            args.deps_file = f'{basename}-{args.acd_version}.deps'

    if args.command == 'build-collection':
        if args.deps_file is None:
            args.deps_file = DEFAULT_FILE_BASE + f'{args.acd_version}.deps'

    return args


async def get_ansible_base_version(aio_session, pypi_server_url=PYPI_SERVER_URL):
    # Retrieve the ansible-base package info from pypi
    query_url = urljoin(pypi_server_url, 'pypi/ansible-base/json')
    async with aio_session.get(query_url) as response:
        pkg_info = await response.json()

    # Calculate the newest version of the package
    return [pkg_info['info']['version']]


def display_exception(loop, context):
    print(context.get('exception'))


async def get_version_info(collections):
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(display_exception)

    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        requestors['_ansible_base'] = asyncio.create_task(get_ansible_base_version(aio_session))
        galaxy_client = GalaxyClient(GALAXY_SERVER_URL, aio_session)

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


def new_acd(args):
    collections = parse_pieces_file(args.pieces_file)
    dependencies = asyncio.run(get_version_info(collections))

    ansible_base_version = dependencies.pop('_ansible_base')[0]
    dependencies = find_latest_compatible(ansible_base_version, dependencies)

    build_filename = os.path.join(args.dest_dir, args.build_file)
    build_file = BuildFile(build_filename)
    build_file.write(args.acd_version, ansible_base_version, dependencies)

    return 0


async def download_collections(deps, download_dir):
    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        for collection_name, version_spec in deps.items():
            downloader = CollectionDownloader(GALAXY_SERVER_URL, aio_session, download_dir)
            requestors[collection_name] = asyncio.create_task(
                downloader.retrieve(collection_name, version_spec, download_dir))

        included_versions = {}
        responses = await asyncio.gather(*requestors.values())
        for idx, collection_name in enumerate(requestors):
            included_versions[collection_name] = responses[idx]

    return included_versions


async def install_collections(version, tmp_dir):
    loop = asyncio.get_running_loop()
    ansible_dir = os.path.join(tmp_dir, f'ansible-{version}')
    os.mkdir(ansible_dir, mode=0o700)
    ansible_collections_dir = os.path.join(ansible_dir, 'ansible_collections')
    os.mkdir(ansible_collections_dir, mode=0o700)

    installers = []
    collection_tarballs = ((p, f) for f in os.listdir(tmp_dir)
                           if os.path.isfile(p := os.path.join(tmp_dir, f)))
    for pathname, filename in collection_tarballs:
        namespace, collection, _dummy = filename.split('-', 2)
        collection_dir = os.path.join(ansible_collections_dir, namespace, collection)
        # Note: this is okay because we created ansible_dir ourselves as a directory
        # that only we can access
        os.makedirs(collection_dir, mode=0o700, exist_ok=False)

        # If the choice of install tools for galaxy is ever settled upon, we can switch from tar to
        # using that
        installers.append(loop.run_in_executor(None, sh.tar, '-xf', pathname, '-C', collection_dir))

    await asyncio.gather(*installers)


def copy_boilerplate_files(package_dir):
    gpl_license = pkgutil.get_data('ansible_infra.data', 'gplv3.txt')
    with open(os.path.join(package_dir, 'COPYING'), 'wb') as f:
        f.write(gpl_license)

    readme = pkgutil.get_data('ansible_infra.data', 'acd-readme.txt')
    with open(os.path.join(package_dir, 'README'), 'wb') as f:
        f.write(readme)


def write_manifest(package_dir):
    manifest_file = os.path.join(package_dir, 'MANIFEST.in')
    with open(manifest_file, 'w') as f:
        f.write('include COPYING\n')
        f.write('include README\n')
        f.write('recursive-include ansible_collections/ **\n')


def write_setup(package_dir, acd_version):
    setup_filename = os.path.join(package_dir, 'setup.py')

    setup_tmpl = Template(pkgutil.get_data('ansible_infra.data', 'setup_py.j2').decode('utf-8'))
    setup_contents = setup_tmpl.render(version=acd_version)

    with open(setup_filename, 'w') as f:
        f.write(setup_contents)


def write_python_build_files(acd_version, dest_dir):
    toplevel_dir = os.path.join(dest_dir, f'ansible-{acd_version}')

    copy_boilerplate_files(toplevel_dir)
    write_manifest(toplevel_dir)
    write_setup(toplevel_dir, acd_version)


def make_dist(ansible_dir, dest_dir):
    sh.python('setup.py', 'sdist', _cwd=ansible_dir)
    dist_dir = os.path.join(ansible_dir, 'dist')
    files = os.listdir(dist_dir)
    if len(files) != 1:
        raise Exception('python setup.py sdist should only have created one file')

    shutil.move(os.path.join(dist_dir, files[0]), dest_dir)


def build_single(args):
    build_file = BuildFile(args.build_file)
    build_acd_version, ansible_base_version, deps = build_file.parse()

    if not str(args.acd_version).startswith(build_acd_version):
        print(f'{args.build_file} is for version {build_acd_version} but we need'
              ' {args.acd_version.major}.{arg.acd_version.minor}')

    with tempfile.TemporaryDirectory() as download_dir:
        included_versions = asyncio.run(download_collections(deps, download_dir))
        asyncio.run(install_collections(args.acd_version, download_dir))
        write_python_build_files(args.acd_version, download_dir)
        make_dist(os.path.join(download_dir, f'ansible-{args.acd_version}'), args.dest_dir)

    deps_filename = os.path.join(args.dest_dir, args.deps_file)
    deps_file = DepsFile(deps_filename)
    deps_file.write(args.acd_version, ansible_base_version, included_versions)

    return 0


def build_multiple(args):
    raise NotImplementedError('build_multiple is not yet implemented')


def build_collection(args):
    with tempfile.TemporaryDirectory() as working_dir:
        collection_dir = os.path.join(working_dir, 'community', 'acd')

        sh.ansible_galaxy('collection', 'init', 'community.acd', '--init-path', working_dir)
        # Copy the README.md file
        readme = pkgutil.get_data('ansible_infra.data', 'README_md.txt')
        with open(os.path.join(collection_dir, 'README.md'), 'wb') as f:
            f.write(readme)

        # Parse the deps file
        deps_file = DepsFile(args.deps_file)
        acd_version, ansible_base_version, deps = deps_file.parse()

        # Template the galaxy.yml file
        dep_string = json.dumps(deps)
        dep_string.replace(', ', ',\n    ')
        galaxy_yml = pkgutil.get_data('ansible_infra.data', 'galaxy_yml.j2').decode('utf-8')
        galaxy_yml_tmpl = Template(galaxy_yml)
        galaxy_yml_contents = galaxy_yml_tmpl.render(version=args.acd_version,
                                                     dependencies=dep_string)

        with open(os.path.join(collection_dir, 'galaxy.yml'), 'w') as f:
            f.write(galaxy_yml_contents)

        sh.ansible_galaxy('collection', 'build', '--output-path', args.dest_dir, collection_dir)


ARGS_MAP = {'new-acd': new_acd,
            'build-single': build_single,
            'build-multiple': build_multiple,
            'build-collection': build_collection,
            }


def main(args):
    program_name = os.path.basename(args[0])
    try:
        args = parse_args(program_name, args[1:])
    except InvalidArgumentError as e:
        print(e)
        return 2

    return ARGS_MAP[args.command](args)
