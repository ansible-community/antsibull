# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

import asyncio
from datetime import datetime
import os
import os.path
import pkgutil
import shutil
import tempfile
from functools import partial

import aiofiles
import aiohttp
import sh
from jinja2 import Template

from .collections import install_separately, install_together
from .dependency_files import BuildFile, DepsFile
from .galaxy import CollectionDownloader


#
# Common code
#

async def download_collections(deps, download_dir):
    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        downloader = CollectionDownloader(aio_session, download_dir)
        for collection_name, version_spec in deps.items():
            requestors[collection_name] = asyncio.create_task(
                downloader.download_latest_matching(collection_name, version_spec))

        included_versions = {}
        responses = await asyncio.gather(*requestors.values())

    # Note: Python dicts have a stable sort order and since we haven't modified the dict since we
    # used requestors.values() to generate responses, requestors and responses therefor have
    # a matching order.
    for collection_name, results in zip(requestors, responses):
        included_versions[collection_name] = results.version

    return included_versions


#
# Single sdist for ansible
#

def copy_boilerplate_files(package_dir):
    gpl_license = pkgutil.get_data('antsibull.data', 'gplv3.txt')
    with open(os.path.join(package_dir, 'COPYING'), 'wb') as f:
        f.write(gpl_license)

    readme = pkgutil.get_data('antsibull.data', 'acd-readme.txt')
    with open(os.path.join(package_dir, 'README'), 'wb') as f:
        f.write(readme)


def write_manifest(package_dir, debian=False):
    manifest_file = os.path.join(package_dir, 'MANIFEST.in')
    with open(manifest_file, 'w') as f:
        f.write('include COPYING\n')
        f.write('include README\n')
        if debian:
            f.write('include debian/*\n')
        f.write('recursive-include ansible_collections/ **\n')


def write_setup(acd_version, collection_deps, package_dir):
    setup_filename = os.path.join(package_dir, 'setup.py')

    setup_tmpl = Template(pkgutil.get_data('antsibull.data', 'acd-setup_py.j2').decode('utf-8'))
    setup_contents = setup_tmpl.render(version=acd_version, collection_deps=collection_deps)

    with open(setup_filename, 'w') as f:
        f.write(setup_contents)


def write_python_build_files(acd_version, collection_deps, package_dir, debian=False):
    copy_boilerplate_files(package_dir)
    write_manifest(package_dir, debian)
    write_setup(acd_version, collection_deps, package_dir)


def write_debian_directory(acd_version, package_dir):
    debian_dir = os.path.join(package_dir, 'debian')
    os.mkdir(debian_dir, mode=0o700)
    debian_files = ('changelog.j2', 'control', 'copyright', 'rules')
    for filename in debian_files:
        # Don't use os.path.join here, the get_data docs say it should be
        # slash-separated.
        src_pkgfile = 'debian/' + filename
        data = pkgutil.get_data('antsibull.data', src_pkgfile).decode('utf-8')

        if filename.endswith('.j2'):
            filename = filename.replace('.j2', '')
            # If the file is a template, send it in vars it might need
            # and update 'data' to be the result.
            tmpl = Template(data)
            data = tmpl.render(
                version=acd_version,
                date=datetime.utcnow().strftime("%a, %d %b %Y %T +0000"),
            )

        with open(os.path.join(debian_dir, filename), 'w') as f:
            f.write(data)


def make_dist(ansible_dir, dest_dir):
    sh.python('setup.py', 'sdist', _cwd=ansible_dir)
    dist_dir = os.path.join(ansible_dir, 'dist')
    files = os.listdir(dist_dir)
    if len(files) != 1:
        raise Exception('python setup.py sdist should only have created one file')

    shutil.move(os.path.join(dist_dir, files[0]), dest_dir)


def build_single_command(args):
    build_file = BuildFile(args.build_file)
    build_acd_version, ansible_base_version, deps = build_file.parse()

    if not str(args.acd_version).startswith(build_acd_version):
        print(f'{args.build_file} is for version {build_acd_version} but we need'
              ' {args.acd_version.major}.{arg.acd_version.minor}')
        return 1

    with tempfile.TemporaryDirectory() as tmp_dir:
        download_dir = os.path.join(tmp_dir, 'collections')
        os.mkdir(download_dir, mode=0o700)

        included_versions = asyncio.run(download_collections(deps, download_dir))

        package_dir = os.path.join(tmp_dir, f'ansible-{args.acd_version}')
        os.mkdir(package_dir, mode=0o700)
        ansible_collections_dir = os.path.join(package_dir, 'ansible_collections')
        os.mkdir(ansible_collections_dir, mode=0o700)

        collections_to_install = [p for f in os.listdir(download_dir)
                                  if os.path.isfile(p := os.path.join(download_dir, f))]
        asyncio.run(install_together(collections_to_install, ansible_collections_dir))
        write_python_build_files(args.acd_version, '', package_dir, args.debian)
        if args.debian:
            write_debian_directory(args.acd_version, package_dir)
        make_dist(package_dir, args.dest_dir)

    deps_filename = os.path.join(args.dest_dir, args.deps_file)
    deps_file = DepsFile(deps_filename)
    deps_file.write(args.acd_version, ansible_base_version, included_versions)

    return 0

#
# Code to make one sdist per collection
#


async def write_collection_readme(collection_name, package_dir):
    readme_tmpl = Template(pkgutil.get_data('antsibull.data',
                                            'collection-readme.j2').decode('utf-8'))
    readme_contents = readme_tmpl.render(collection_name=collection_name)

    readme_filename = os.path.join(package_dir, 'README.rst')
    async with aiofiles.open(readme_filename, 'w') as f:
        await f.write(readme_contents)


async def write_collection_setup(name, version, package_dir):
    setup_filename = os.path.join(package_dir, 'setup.py')

    setup_tmpl = Template(pkgutil.get_data('antsibull.data',
                                           'collection-setup_py.j2').decode('utf-8'))
    setup_contents = setup_tmpl.render(version=version, name=name)

    async with aiofiles.open(setup_filename, 'w') as f:
        await f.write(setup_contents)


async def write_collection_manifest(package_dir):
    manifest_file = os.path.join(package_dir, 'MANIFEST.in')
    async with aiofiles.open(manifest_file, 'w') as f:
        await f.write('include README.rst\n')
        await f.write('recursive-include ansible_collections/ **\n')


async def make_collection_dist(name, version, package_dir, dest_dir):
    # Copy boilerplate into place
    await write_collection_readme(name, package_dir)
    await write_collection_setup(name, version, package_dir)
    await write_collection_manifest(package_dir)

    loop = asyncio.get_running_loop()

    # Create the python sdist
    await loop.run_in_executor(None, partial(sh.python, 'setup.py', 'sdist', _cwd=package_dir))
    dist_dir = os.path.join(package_dir, 'dist')
    files = os.listdir(dist_dir)
    if len(files) != 1:
        raise Exception('python setup.py sdist should only have created one file')

    dist_file = os.path.join(dist_dir, files[0])
    await loop.run_in_executor(None, shutil.move, dist_file, dest_dir)


async def make_collection_dists(dest_dir, collection_dirs):
    dist_creators = []
    for collection_dir in collection_dirs:
        dir_name_only = os.path.basename(collection_dir)
        dummy_, dummy_, name, version = dir_name_only.split('-', 3)

        dist_creators.append(asyncio.create_task(
            make_collection_dist(name, version, collection_dir, dest_dir)))

    await asyncio.gather(*dist_creators)


def build_multiple_command(args):
    build_file = BuildFile(args.build_file)
    build_acd_version, ansible_base_version, deps = build_file.parse()

    if not str(args.acd_version).startswith(build_acd_version):
        print(f'{args.build_file} is for version {build_acd_version} but we need'
              f' {args.acd_version.major}.{args.acd_version.minor}')
        return 1

    with tempfile.TemporaryDirectory() as tmp_dir:
        download_dir = os.path.join(tmp_dir, 'collections')
        os.mkdir(download_dir, mode=0o700)

        included_versions = asyncio.run(download_collections(deps, download_dir))
        collections_to_install = [p for f in os.listdir(download_dir)
                                  if os.path.isfile(p := os.path.join(download_dir, f))]
        collection_dirs = asyncio.run(install_separately(collections_to_install, download_dir))
        asyncio.run(make_collection_dists(args.dest_dir, collection_dirs))

        # Create the ansible package that deps on the collections we just wrote
        package_dir = os.path.join(tmp_dir, f'ansible-{args.acd_version}')
        os.mkdir(package_dir, mode=0o700)
        ansible_collections_dir = os.path.join(package_dir, 'ansible_collections')
        os.mkdir(ansible_collections_dir, mode=0o700)

        # Construct the list of dependent collection packages
        collection_deps = []
        for collection, version in sorted(included_versions.items()):
            collection_deps.append(f"        '{collection}>={version},<{version.next_major()}'")
        collection_deps = '\n' + ',\n'.join(collection_deps)
        write_python_build_files(args.acd_version, collection_deps, package_dir)

        make_dist(package_dir, args.dest_dir)

    # Write the deps file
    deps_filename = os.path.join(args.dest_dir, args.deps_file)
    deps_file = DepsFile(deps_filename)
    deps_file.write(args.acd_version, ansible_base_version, included_versions)

    return 0
