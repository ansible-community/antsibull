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
import typing as t
from functools import partial

import aiofiles
import aiohttp
import asyncio_pool
import sh
from jinja2 import Template
from packaging.version import Version as PypiVer

from . import app_context
from .build_changelog import ReleaseNotes
from .changelog import get_changelog
from .collections import install_separately, install_together
from .dependency_files import BuildFile, DependencyFileData, DepsFile
from .galaxy import CollectionDownloader


#
# Common code
#


async def download_collections(deps, galaxy_url, download_dir, collection_cache=None):
    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        lib_ctx = app_context.lib_ctx.get()
        async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
            downloader = CollectionDownloader(aio_session, download_dir,
                                              collection_cache=collection_cache,
                                              galaxy_server=galaxy_url)
            for collection_name, version_spec in deps.items():
                requestors[collection_name] = await pool.spawn(
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

    readme = pkgutil.get_data('antsibull.data', 'acd-readme.rst')
    with open(os.path.join(package_dir, 'README.rst'), 'wb') as f:
        f.write(readme)


def write_manifest(package_dir, release_notes: t.Optional[ReleaseNotes] = None,
                   debian: bool = False):
    manifest_file = os.path.join(package_dir, 'MANIFEST.in')
    with open(manifest_file, 'w') as f:
        f.write('include COPYING\n')
        f.write('include README\n')
        f.write('include build-ansible.sh\n')
        if release_notes:
            f.write('include {0}\n'.format(release_notes.changelog_filename))
            f.write('include {0}\n'.format(release_notes.porting_guide_filename))
        if debian:
            f.write('include debian/*\n')
        f.write('recursive-include ansible_collections/ **\n')


def write_setup(acd_version, ansible_base_version, collection_deps, package_dir):
    setup_filename = os.path.join(package_dir, 'setup.py')

    setup_tmpl = Template(pkgutil.get_data('antsibull.data', 'acd-setup_py.j2').decode('utf-8'))
    setup_contents = setup_tmpl.render(version=acd_version,
                                       ansible_base_version=ansible_base_version,
                                       collection_deps=collection_deps)

    with open(setup_filename, 'w') as f:
        f.write(setup_contents)


def write_python_build_files(acd_version, ansible_base_version, collection_deps, package_dir,
                             release_notes: t.Optional[ReleaseNotes] = None, debian: bool = False):
    copy_boilerplate_files(package_dir)
    write_manifest(package_dir, release_notes, debian)
    write_setup(acd_version, ansible_base_version, collection_deps, package_dir)


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


def write_build_script(acd_version, ansible_base_version, package_dir):
    """Write a build-script that tells how to build this tarball."""
    build_ansible_filename = os.path.join(package_dir, 'build-ansible.sh')

    build_ansible_tmpl = Template(pkgutil.get_data('antsibull.data',
                                                   'build-ansible.sh.j2').decode('utf-8'))
    build_ansible_contents = build_ansible_tmpl.render(version=acd_version,
                                                       ansible_base_version=ansible_base_version)

    with open(build_ansible_filename, 'w') as f:
        f.write(build_ansible_contents)
    os.chmod(build_ansible_filename, mode=0o755)


def build_single_command():
    app_ctx = app_context.app_ctx.get()

    build_file = BuildFile(app_ctx.extra['build_file'])
    build_acd_version, ansible_base_version, deps = build_file.parse()
    ansible_base_version = PypiVer(ansible_base_version)

    if not str(app_ctx.extra['acd_version']).startswith(build_acd_version):
        print(f'{app_ctx.extra["build_file"]} is for version {build_acd_version} but we need'
              f' {app_ctx.extra["acd_version"].major}.{app_ctx.extra["acd_version"].minor}')
        return 1

    with tempfile.TemporaryDirectory() as tmp_dir:
        download_dir = os.path.join(tmp_dir, 'collections')
        os.mkdir(download_dir, mode=0o700)

        # Download included collections
        included_versions = asyncio.run(download_collections(deps, app_ctx.galaxy_url,
                                                             download_dir,
                                                             app_ctx.extra['collection_cache']))

        new_dependencies = DependencyFileData(
            str(app_ctx.extra["acd_version"]),
            str(ansible_base_version),
            {collection: str(version) for collection, version in included_versions.items()})

        # Get changelog and porting guide data
        deps_dir = os.path.dirname(
            os.path.join(app_ctx.extra["dest_dir"], app_ctx.extra["deps_file"]))
        changelog = get_changelog(
            app_ctx.extra["acd_version"],
            deps_dir=deps_dir,
            deps_data=[new_dependencies],
            collection_cache=app_ctx.extra["collection_cache"])

        # Create package and collections directories
        package_dir = os.path.join(tmp_dir, f'ansible-{app_ctx.extra["acd_version"]}')
        os.mkdir(package_dir, mode=0o700)
        ansible_collections_dir = os.path.join(package_dir, 'ansible_collections')
        os.mkdir(ansible_collections_dir, mode=0o700)

        # Install collections
        # TODO: PY3.8:
        # collections_to_install = [p for f in os.listdir(download_dir)
        #                           if os.path.isfile(p := os.path.join(download_dir, f))]
        collections_to_install = []
        for collection in os.listdir(download_dir):
            path = os.path.join(download_dir, collection)
            if os.path.isfile(path):
                collections_to_install.append(path)

        asyncio.run(install_together(collections_to_install, ansible_collections_dir))

        # Compose and write release notes
        release_notes = ReleaseNotes.build(changelog)
        release_notes.write_changelog_to(package_dir)
        # TODO: include porting guide after discussion in DaWG meeting about its relation
        #       to the ansible-base porting guide, and where things will be placed and
        #       structured.
        # release_notes.write_porting_guide_to(package_dir)

        # Write build scripts and files
        write_build_script(app_ctx.extra['acd_version'], ansible_base_version, package_dir)
        write_python_build_files(app_ctx.extra['acd_version'], ansible_base_version, '',
                                 package_dir, release_notes, app_ctx.extra['debian'])
        if app_ctx.extra['debian']:
            write_debian_directory(app_ctx.extra['acd_version'], package_dir)
        make_dist(package_dir, app_ctx.extra['dest_dir'])

    deps_filename = os.path.join(app_ctx.extra['dest_dir'], app_ctx.extra['deps_file'])
    deps_file = DepsFile(deps_filename)
    deps_file.write(
        new_dependencies.ansible_version,
        new_dependencies.ansible_base_version,
        new_dependencies.deps)

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
    lib_ctx = app_context.lib_ctx.get()
    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        for collection_dir in collection_dirs:
            dir_name_only = os.path.basename(collection_dir)
            dummy_, dummy_, name, version = dir_name_only.split('-', 3)

            dist_creators.append(await pool.spawn(
                make_collection_dist(name, version, collection_dir, dest_dir)))

        await asyncio.gather(*dist_creators)


def build_multiple_command():
    app_ctx = app_context.app_ctx.get()

    build_file = BuildFile(app_ctx.extra['build_file'])
    build_acd_version, ansible_base_version, deps = build_file.parse()
    ansible_base_version = PypiVer(ansible_base_version)

    if not str(app_ctx.extra['acd_version']).startswith(build_acd_version):
        print(f'{app_ctx.extra["build_file"]} is for version {build_acd_version} but we need'
              f' {app_ctx.extra["acd_version"].major}.{app_ctx.extra["acd_version"].minor}')
        return 1

    with tempfile.TemporaryDirectory() as tmp_dir:
        download_dir = os.path.join(tmp_dir, 'collections')
        os.mkdir(download_dir, mode=0o700)

        included_versions = asyncio.run(
            download_collections(deps, app_ctx.galaxy_url, download_dir,
                                 app_ctx.extra['collection_cache']))
        # TODO: PY3.8:
        # collections_to_install = [p for f in os.listdir(download_dir)
        #                           if os.path.isfile(p := os.path.join(download_dir, f))]
        collections_to_install = []
        for collection in os.listdir(download_dir):
            path = os.path.join(download_dir, collection)
            if os.path.isfile(path):
                collections_to_install.append(path)

        collection_dirs = asyncio.run(install_separately(collections_to_install, download_dir))
        asyncio.run(make_collection_dists(app_ctx.extra['dest_dir'], collection_dirs))

        # Create the ansible package that deps on the collections we just wrote
        package_dir = os.path.join(tmp_dir, f'ansible-{app_ctx.extra["acd_version"]}')
        os.mkdir(package_dir, mode=0o700)
        ansible_collections_dir = os.path.join(package_dir, 'ansible_collections')
        os.mkdir(ansible_collections_dir, mode=0o700)

        # Construct the list of dependent collection packages
        collection_deps = []
        for collection, version in sorted(included_versions.items()):
            collection_deps.append(f"        '{collection}>={version},<{version.next_major()}'")
        collection_deps = '\n' + ',\n'.join(collection_deps)
        write_build_script(app_ctx.extra['acd_version'], ansible_base_version, package_dir)
        write_python_build_files(app_ctx.extra['acd_version'], ansible_base_version,
                                 collection_deps, package_dir)

        make_dist(package_dir, app_ctx.extra['dest_dir'])

    # Write the deps file
    deps_filename = os.path.join(app_ctx.extra['dest_dir'], app_ctx.extra['deps_file'])
    deps_file = DepsFile(deps_filename)
    deps_file.write(app_ctx.extra['acd_version'], ansible_base_version, included_versions)

    return 0
