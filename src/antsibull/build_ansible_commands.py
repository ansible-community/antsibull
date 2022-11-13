# Author: Toshio Kuratomi <tkuratom@redhat.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020
"""Build Ansible packages."""

import asyncio
import datetime
import os
import os.path
import shutil
import tempfile
import typing as t
from functools import partial

import aiofiles
import aiohttp
import asyncio_pool  # type: ignore[import]
import sh
from jinja2 import Template
from packaging.version import Version as PypiVer
from semantic_version import Version as SemVer, SimpleSpec as SemVerSpec

from antsibull_core import app_context
from antsibull_core.ansible_core import get_ansible_core_package_name, AnsibleCorePyPiClient
from antsibull_core.collections import install_separately, install_together
from antsibull_core.compat import asyncio_run
from antsibull_core.dependency_files import BuildFile, DependencyFileData, DepsFile
from antsibull_core.galaxy import CollectionDownloader, GalaxyClient
from antsibull_core.logging import log
from antsibull_core.utils.io import write_file
from antsibull_core.yaml import store_yaml_file

from .build_changelog import ReleaseNotes
from .changelog import ChangelogData, get_changelog
from .dep_closure import check_collection_dependencies
from .utils.get_pkg_data import get_antsibull_data


mlog = log.fields(mod=__name__)


#
# Common code
#


async def get_latest_ansible_core_version(ansible_core_version: PypiVer,
                                          client: AnsibleCorePyPiClient,
                                          pre: bool = False) -> t.Optional[PypiVer]:
    """
    Retrieve the latest ansible-core bugfix release's version for the given ansible-core version.

    :arg ansible_core_version: The ansible-core version.
    :arg client: A AnsibleCorePyPiClient instance.
    """
    all_versions = await client.get_versions()
    next_version = PypiVer(f'{ansible_core_version.major}.{ansible_core_version.minor + 1}a')
    newer_versions = [
        version for version in all_versions
        if ansible_core_version <= version < next_version
        and (pre or not version.is_prerelease)
    ]
    return max(newer_versions) if newer_versions else None


async def get_collection_and_core_versions(deps: t.Mapping[str, str],
                                           ansible_core_version: t.Optional[PypiVer],
                                           galaxy_url: str,
                                           ansible_core_allow_prerelease: bool = False,
                                           ) -> t.Tuple[t.Dict[str, SemVer], t.Optional[PypiVer]]:
    """
    Retrieve the latest version of each collection.

    :arg deps: Mapping of collection name to a version specification.
    :arg ansible_core_version: Optional ansible-core version. Will search for the latest bugfix
        release.
    :arg galaxy_url: The url for the galaxy server to use.
    :arg ansible_core_allow_prerelease: Whether to allow prereleases for ansible-core
    :returns: Tuple consisting of a dict mapping collection name to latest version, and of the
        ansible-core version if it was provided.
    """
    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        lib_ctx = app_context.lib_ctx.get()
        async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
            client = GalaxyClient(aio_session, galaxy_server=galaxy_url)
            for collection_name, version_spec in deps.items():
                requestors[collection_name] = await pool.spawn(
                    client.get_latest_matching_version(collection_name, version_spec, pre=True))
            if ansible_core_version:
                requestors['_ansible_core'] = await pool.spawn(get_latest_ansible_core_version(
                    ansible_core_version, AnsibleCorePyPiClient(aio_session),
                    pre=ansible_core_allow_prerelease))

            responses = await asyncio.gather(*requestors.values())

    # Note: Python dicts have a stable sort order and since we haven't modified the dict since we
    # used requestors.values() to generate responses, requestors and responses therefore have
    # a matching order.
    included_versions: t.Dict[str, SemVer] = {}
    for collection_name, version in zip(requestors, responses):
        if collection_name == '_ansible_core':
            ansible_core_version = version
        else:
            included_versions[collection_name] = version

    return included_versions, ansible_core_version


async def get_collection_versions(deps: t.Mapping[str, str],
                                  galaxy_url: str,
                                  ) -> t.Dict[str, SemVer]:
    """
    Retrieve the latest version of each collection.

    :arg deps: Mapping of collection name to a version specification.
    :arg galaxy_url: The url for the galaxy server to use.
    :returns: Dict mapping collection name to latest version.
    """
    return (await get_collection_and_core_versions(deps, None, galaxy_url))[0]


async def download_collections(versions: t.Mapping[str, SemVer],
                               galaxy_url: str,
                               download_dir: str,
                               collection_cache: t.Optional[str] = None,
                               ) -> None:
    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        lib_ctx = app_context.lib_ctx.get()
        async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
            downloader = CollectionDownloader(aio_session, download_dir,
                                              collection_cache=collection_cache,
                                              galaxy_server=galaxy_url)
            for collection_name, version in versions.items():
                requestors[collection_name] = await pool.spawn(
                    downloader.download(collection_name, version))

            await asyncio.gather(*requestors.values())


#
# Single sdist for ansible
#

def copy_boilerplate_files(package_dir: str) -> None:
    gpl_license = get_antsibull_data('gplv3.txt')
    with open(os.path.join(package_dir, 'COPYING'), 'wb') as f:
        f.write(gpl_license)

    readme = get_antsibull_data('ansible-readme.rst')
    with open(os.path.join(package_dir, 'README.rst'), 'wb') as f:
        f.write(readme)


def write_manifest(package_dir: str,
                   release_notes: t.Optional[ReleaseNotes] = None,
                   debian: bool = False) -> None:
    manifest_file = os.path.join(package_dir, 'MANIFEST.in')
    with open(manifest_file, 'w', encoding='utf-8') as f:
        f.write('include COPYING\n')
        f.write('include README.rst\n')
        f.write('include build-ansible.sh\n')
        if release_notes:
            f.write(f'include {release_notes.changelog_filename}\n')
            f.write(f'include {release_notes.porting_guide_filename}\n')
        if debian:
            f.write('include debian/*\n')
        f.write('recursive-include ansible_collections/ **\n')


def write_release_py(ansible_version: PypiVer, ansible_collections_dir: str) -> None:
    release_filename = os.path.join(ansible_collections_dir, 'ansible_release.py')

    release_tmpl = Template(get_antsibull_data('ansible-release_py.j2').decode('utf-8'))
    release_contents = release_tmpl.render(version=ansible_version)

    with open(release_filename, 'w', encoding='utf-8') as f:
        f.write(release_contents)


def write_ansible_community_py(ansible_version: PypiVer, ansible_collections_dir: str) -> None:
    release_filename = os.path.join(ansible_collections_dir, 'ansible_community.py')

    release_tmpl = Template(get_antsibull_data('ansible-community.py.j2').decode('utf-8'))
    release_contents = release_tmpl.render(version=ansible_version)

    with open(release_filename, 'w', encoding='utf-8') as f:
        f.write(release_contents + '\n')


def write_setup(ansible_version: PypiVer,
                ansible_core_version: PypiVer,
                collection_exclude_paths: t.List[str],
                collection_deps: str,
                package_dir: str,
                python_requires: str) -> None:
    setup_filename = os.path.join(package_dir, 'setup.py')

    setup_tmpl = Template(get_antsibull_data('ansible-setup_py.j2').decode('utf-8'))
    setup_contents = setup_tmpl.render(
        version=ansible_version,
        ansible_core_package_name=get_ansible_core_package_name(ansible_core_version),
        ansible_core_version=ansible_core_version,
        collection_exclude_paths=collection_exclude_paths,
        collection_deps=collection_deps,
        python_requires=python_requires,
        PypiVer=PypiVer,
    )

    with open(setup_filename, 'w', encoding='utf-8') as f:
        f.write(setup_contents)


def write_python_build_files(ansible_version: PypiVer,
                             ansible_core_version: PypiVer,
                             collection_exclude_paths: t.List[str],
                             collection_deps: str,
                             package_dir: str,
                             release_notes: t.Optional[ReleaseNotes] = None,
                             debian: bool = False,
                             python_requires: str = '>=3.8') -> None:
    copy_boilerplate_files(package_dir)
    write_manifest(package_dir, release_notes, debian)
    write_setup(
        ansible_version, ansible_core_version, collection_exclude_paths, collection_deps,
        package_dir, python_requires)


def write_debian_directory(ansible_version: PypiVer,
                           ansible_core_version: PypiVer,
                           package_dir: str) -> None:
    debian_dir = os.path.join(package_dir, 'debian')
    os.mkdir(debian_dir, mode=0o700)
    debian_files = ('changelog.j2', 'control.j2', 'copyright', 'rules')
    ansible_core_package_name = get_ansible_core_package_name(ansible_core_version)
    for filename in debian_files:
        # Don't use os.path.join here, the get_data docs say it should be
        # slash-separated.
        src_pkgfile = 'debian/' + filename
        data = get_antsibull_data(src_pkgfile).decode('utf-8')

        if filename.endswith('.j2'):
            filename = filename.replace('.j2', '')
            # If the file is a template, send it in vars it might need
            # and update 'data' to be the result.
            tmpl = Template(data)
            data = tmpl.render(
                version=str(ansible_version),
                date=datetime.datetime.utcnow().strftime('%a, %d %b %Y %T +0000'),
                ansible_core_package_name=ansible_core_package_name,
            )

        with open(os.path.join(debian_dir, filename), 'w', encoding='utf-8') as f:
            f.write(data)


def write_galaxy_requirements(filename: str, included_versions: t.Mapping[str, str]) -> None:
    galaxy_reqs = []
    for collection, version in sorted(included_versions.items()):
        galaxy_reqs.append({
            'name': collection,
            'version': version,
            'source': 'https://galaxy.ansible.com'
        })

    store_yaml_file(filename, {
        'collections': galaxy_reqs,
    })


def show_warnings(result: sh.RunningCommand, **kwargs) -> None:
    stderr = result.stderr.decode('utf-8').strip()
    if stderr:
        logger = mlog.fields(**kwargs)
        for line in stderr.splitlines():
            logger.warning(line)


def make_dist(ansible_dir: str, dest_dir: str) -> None:
    show_warnings(
        # pyre-ignore[16], pylint:disable-next=no-member
        sh.python('setup.py', 'sdist', _cwd=ansible_dir),
        func='make_dist',
    )
    dist_dir = os.path.join(ansible_dir, 'dist')
    files = os.listdir(dist_dir)
    if len(files) != 1:
        raise Exception('python setup.py sdist should only have created one file')

    shutil.move(os.path.join(dist_dir, files[0]), dest_dir)


def make_dist_with_wheels(ansible_dir: str, dest_dir: str) -> None:
    show_warnings(
        # pyre-ignore[16], pylint:disable-next=no-member
        sh.python('setup.py', 'sdist', 'bdist_wheel', _cwd=ansible_dir),
        func='make_dist_with_wheels',
    )
    dist_dir = os.path.join(ansible_dir, 'dist')
    files = os.listdir(dist_dir)
    tarball_count = 0
    wheel_count = 0
    for file in files:
        if file.endswith('.tar') or file.endswith('.tar.gz'):
            tarball_count += 1
        elif file.endswith('.whl'):
            wheel_count += 1
        else:
            tarball_count = 2  # the number is wrong, but this triggers an error
            break
    if tarball_count != 1 or wheel_count == 0:
        raise Exception(
            "python setup.py sdist bdist_wheel should have created exactly one tarball and at"
            f" least one wheel (got {files})")

    for file in files:
        shutil.move(os.path.join(dist_dir, file), dest_dir)


def write_build_script(ansible_version: PypiVer,
                       ansible_core_version: PypiVer,
                       package_dir: str) -> None:
    """Write a build-script that tells how to build this tarball."""
    build_ansible_filename = os.path.join(package_dir, 'build-ansible.sh')

    build_ansible_tmpl = Template(get_antsibull_data('build-ansible.sh.j2').decode('utf-8'))
    build_ansible_contents = build_ansible_tmpl.render(version=ansible_version,
                                                       ansible_core_version=ansible_core_version)

    with open(build_ansible_filename, 'w', encoding='utf-8') as f:
        f.write(build_ansible_contents)
    os.chmod(build_ansible_filename, mode=0o755)


def build_single_command() -> int:
    # This is deprecated; in the future users will have to first run prepare, and then
    # rebuild-single.
    result = prepare_command()
    if result != 0:
        return result

    return rebuild_single_command()


def _is_alpha(version: PypiVer) -> bool:
    """Test whether the provided version is an alpha version."""
    pre = version.pre
    return version.is_prerelease and pre is not None and pre[0] == 'a'


def _extract_python_requires(ansible_core_version: PypiVer, deps: t.Dict[str, str]) -> str:
    python_requires = deps.pop('_python', None)
    if python_requires is not None:
        return python_requires
    if ansible_core_version < PypiVer('2.12.0a'):
        # Ansible 2.9, ansible-base 2.10, and ansible-core 2.11 support Python 2.7 and Python 3.5+
        return '>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*'
    if ansible_core_version < PypiVer('2.14.0a'):
        # ansible-core 2.12 and 2.13 support Python 3.8+
        return '>=3.8'
    if ansible_core_version < PypiVer('2.15.0a'):
        # ansible-core 2.14 supports Python 3.9+
        return '>=3.9'
    raise ValueError(
        f'Python requirements for ansible-core {ansible_core_version} should be part of'
        ' dependency information')


def prepare_command() -> int:
    app_ctx = app_context.app_ctx.get()

    build_filename = os.path.join(app_ctx.extra['data_dir'], app_ctx.extra['build_file'])
    build_file = BuildFile(build_filename)
    build_ansible_version, ansible_core_version, deps = build_file.parse()
    ansible_core_version_obj = PypiVer(ansible_core_version)
    python_requires = _extract_python_requires(ansible_core_version_obj, deps)

    # If we're building a feature frozen release (betas and rcs) then we need to
    # change the upper version limit to not include new features.
    if app_ctx.extra['feature_frozen']:
        old_deps, deps = deps, {}
        # For each collection that's listed...
        for collection_name, spec in old_deps.items():
            spec_obj = SemVerSpec(spec)
            new_clauses = []
            min_version = None

            # Look at each clause of the version specification
            for clause in spec_obj.clause.clauses:
                if clause.operator in ('<', '<='):
                    # Omit the upper bound as we're replacing it
                    continue

                if clause.operator == '>=':
                    # Save the lower bound so we can write out a new compatible version
                    min_version = clause.target

                new_clauses.append(str(clause))

            if min_version is None:
                raise ValueError(f'No minimum version specified for {collection_name}: {spec_obj}')

            new_clauses.append(f'<{min_version.major}.{min_version.minor + 1}.0')
            deps[collection_name] = ','.join(new_clauses)

    included_versions, new_ansible_core_version = asyncio_run(
        get_collection_and_core_versions(
            deps, ansible_core_version_obj, app_ctx.galaxy_url,
            ansible_core_allow_prerelease=_is_alpha(app_ctx.extra['ansible_version'])))
    if new_ansible_core_version:
        ansible_core_version_obj = new_ansible_core_version

    if not str(app_ctx.extra['ansible_version']).startswith(build_ansible_version):
        print(f'{build_filename} is for version {build_ansible_version} but we need'
              f' {app_ctx.extra["ansible_version"].major}'
              f'.{app_ctx.extra["ansible_version"].minor}')
        return 1

    dependency_data = DependencyFileData(
        str(app_ctx.extra['ansible_version']),
        str(ansible_core_version_obj),
        {collection: str(version) for collection, version in included_versions.items()})

    # Get Ansible changelog, add new release
    ansible_changelog = ChangelogData.ansible(
        app_ctx.extra['data_dir'], app_ctx.extra['dest_data_dir'])
    date = datetime.date.today()
    ansible_changelog.add_ansible_release(
        str(app_ctx.extra['ansible_version']),
        date,
        f'Release Date: {date}'
        f'\n\n'
        f'`Porting Guide <https://docs.ansible.com/ansible/devel/porting_guides.html>`_')
    ansible_changelog.changes.save()

    # Write dependency file
    deps_filename = os.path.join(app_ctx.extra['dest_data_dir'], app_ctx.extra['deps_file'])
    deps_file = DepsFile(deps_filename)
    deps_file.write(
        dependency_data.ansible_version,
        dependency_data.ansible_core_version,
        dependency_data.deps,
        python_requires=python_requires)

    # Write Galaxy requirements.yml file
    galaxy_filename = os.path.join(app_ctx.extra['dest_data_dir'], app_ctx.extra['galaxy_file'])
    write_galaxy_requirements(galaxy_filename, dependency_data.deps)

    return 0


def compile_collection_exclude_paths(collection_names: t.Collection[str],
                                     collection_root: str) -> t.Tuple[t.List[str], t.List[str]]:
    result = set()
    ignored_files = set()
    all_files: t.List[str] = []
    for collection_name in collection_names:
        namespace, name = collection_name.split('.', 1)
        prefix = f"{namespace}/{name}/"

        # Check files
        collection_dir = os.path.join(collection_root, namespace, name)
        all_files.clear()
        for directory, _, files in os.walk(collection_dir):
            directory = os.path.relpath(directory, collection_dir)
            for file in files:
                all_files.append(os.path.normpath(os.path.join(directory, file)))

        def ignore_file(prefix: str, filename: str):  # pylint: disable=unused-variable
            if filename in all_files:
                result.add(prefix + filename)
                ignored_files.add(prefix + filename)

        def ignore_start(prefix: str, start: str):
            matching_files = [file for file in all_files if file.startswith(start)]
            if matching_files:
                result.add(prefix + start + '*')
                ignored_files.update([prefix + file for file in matching_files])

        def ignore_directory(prefix: str, directory: str):
            directory = directory.rstrip('/') + '/'
            matching_files = [file for file in all_files if file.startswith(directory)]
            if matching_files:
                result.add(prefix + directory + '*')
                ignored_files.update([prefix + file for file in matching_files])

        ignore_start(prefix, '.')
        ignore_directory(prefix, 'docs')
        ignore_directory(prefix, 'tests')
    return sorted(result), sorted(ignored_files)


def rebuild_single_command() -> int:
    app_ctx = app_context.app_ctx.get()

    deps_filename = os.path.join(app_ctx.extra['data_dir'], app_ctx.extra['deps_file'])
    deps_file = DepsFile(deps_filename)
    dependency_data = deps_file.parse()
    python_requires = _extract_python_requires(
        PypiVer(dependency_data.ansible_core_version), dependency_data.deps)

    # Determine included collection versions
    ansible_core_version = PypiVer(dependency_data.ansible_core_version)
    included_versions = {
        collection: SemVer(version)
        for collection, version in dependency_data.deps.items()
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        download_dir = os.path.join(tmp_dir, 'collections')
        os.mkdir(download_dir, mode=0o700)

        # Download included collections
        asyncio_run(download_collections(included_versions, app_ctx.galaxy_url,
                                         download_dir, app_ctx.collection_cache))

        # Get Ansible changelog, add new release
        ansible_changelog = ChangelogData.ansible(
            app_ctx.extra['data_dir'], app_ctx.extra['dest_data_dir'])

        # Get changelog and porting guide data
        changelog = get_changelog(
            app_ctx.extra['ansible_version'],
            deps_dir=app_ctx.extra['data_dir'],
            deps_data=[dependency_data],
            collection_cache=app_ctx.collection_cache,
            ansible_changelog=ansible_changelog)

        # Create package and collections directories
        package_dir = os.path.join(tmp_dir, f'ansible-{app_ctx.extra["ansible_version"]}')
        os.mkdir(package_dir, mode=0o700)
        ansible_collections_dir = os.path.join(package_dir, 'ansible_collections')
        os.mkdir(ansible_collections_dir, mode=0o700)

        # Write the ansible release info to the collections dir
        write_release_py(app_ctx.extra['ansible_version'], ansible_collections_dir)

        # Write the ansible-community CLI program (starting with Ansible 6.0.0rc1)
        if app_ctx.extra['ansible_version'] >= PypiVer('6.0.0rc1'):
            write_ansible_community_py(app_ctx.extra['ansible_version'], ansible_collections_dir)

        # Install collections
        # TODO: PY3.8:
        # collections_to_install = [p for f in os.listdir(download_dir)
        #                           if os.path.isfile(p := os.path.join(download_dir, f))]
        collections_to_install = []
        for collection in os.listdir(download_dir):
            path = os.path.join(download_dir, collection)
            if os.path.isfile(path):
                collections_to_install.append(path)

        asyncio_run(install_together(collections_to_install, ansible_collections_dir))

        # Compose and write release notes to destination directory
        release_notes = ReleaseNotes.build(changelog)
        release_notes.write_changelog_to(package_dir)
        release_notes.write_porting_guide_to(package_dir)

        # Write changelog and porting guide also to destination directory
        release_notes.write_changelog_to(app_ctx.extra['dest_data_dir'])
        release_notes.write_porting_guide_to(app_ctx.extra['dest_data_dir'])

        # pylint:disable-next=unused-variable
        collection_exclude_paths, collection_ignored_files = compile_collection_exclude_paths(
            dependency_data.deps, ansible_collections_dir)

        # TODO: do something with collection_ignored_files

        # Write build scripts and files
        write_build_script(app_ctx.extra['ansible_version'], ansible_core_version, package_dir)
        write_python_build_files(app_ctx.extra['ansible_version'], ansible_core_version,
                                 collection_exclude_paths, '', package_dir, release_notes,
                                 app_ctx.extra['debian'], python_requires)
        if app_ctx.extra['debian']:
            write_debian_directory(app_ctx.extra['ansible_version'], ansible_core_version,
                                   package_dir)

        if app_ctx.extra.get('sdist_src_dir'):
            shutil.copytree(
                package_dir,
                app_ctx.extra['sdist_src_dir'],
                symlinks=True,
                ignore_dangling_symlinks=True)

        # Check dependencies
        dep_errors = check_collection_dependencies(os.path.join(package_dir, 'ansible_collections'))

        if dep_errors:
            is_error = app_ctx.extra["ansible_version"] >= PypiVer('6.3.0')
            warning_error = 'ERROR' if is_error else 'WARNING'
            print(f'{warning_error}: found collection dependency errors!')
            for error in dep_errors:
                print(f'{warning_error}: {error}')
            if is_error:
                return 3

        # Create source distribution
        if app_ctx.extra["ansible_version"].major < 6:
            make_dist(package_dir, app_ctx.extra['sdist_dir'])
        else:
            make_dist_with_wheels(package_dir, app_ctx.extra['sdist_dir'])

    return 0


#
# Code to make one sdist per collection
#


async def write_collection_readme(collection_name: str, package_dir: str) -> None:
    readme_tmpl = Template(get_antsibull_data('collection-readme.j2').decode('utf-8'))
    readme_contents = readme_tmpl.render(collection_name=collection_name)

    readme_filename = os.path.join(package_dir, 'README.rst')
    await write_file(readme_filename, readme_contents)


async def write_collection_setup(name: str, version: str, package_dir: str) -> None:
    setup_filename = os.path.join(package_dir, 'setup.py')

    setup_tmpl = Template(get_antsibull_data('collection-setup_py.j2').decode('utf-8'))
    setup_contents = setup_tmpl.render(version=version, name=name)

    await write_file(setup_filename, setup_contents)


async def write_collection_manifest(package_dir: str) -> None:
    manifest_file = os.path.join(package_dir, 'MANIFEST.in')
    async with aiofiles.open(manifest_file, 'w') as f:
        await f.write('include README.rst\n')
        await f.write('recursive-include ansible_collections/ **\n')


async def make_collection_dist(name: str,
                               version: str,
                               package_dir: str,
                               dest_dir: str) -> None:
    # Copy boilerplate into place
    await write_collection_readme(name, package_dir)
    await write_collection_setup(name, version, package_dir)
    await write_collection_manifest(package_dir)

    loop = asyncio.get_running_loop()

    # Create the python sdist
    # pyre-ignore[16], pylint:disable=no-member
    await loop.run_in_executor(None, partial(sh.python, 'setup.py', 'sdist', _cwd=package_dir))
    dist_dir = os.path.join(package_dir, 'dist')
    files = os.listdir(dist_dir)
    if len(files) != 1:
        raise Exception('python setup.py sdist should only have created one file')

    dist_file = os.path.join(dist_dir, files[0])
    await loop.run_in_executor(None, shutil.move, dist_file, dest_dir)


async def make_collection_dists(dest_dir: str, collection_dirs: t.List[str]) -> None:
    dist_creators = []
    lib_ctx = app_context.lib_ctx.get()
    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        for collection_dir in collection_dirs:
            dir_name_only = os.path.basename(collection_dir)
            dummy_, dummy_, name, version = dir_name_only.split('-', 3)

            dist_creators.append(await pool.spawn(
                make_collection_dist(name, version, collection_dir, dest_dir)))

        await asyncio.gather(*dist_creators)


def build_multiple_command() -> int:
    app_ctx = app_context.app_ctx.get()

    build_filename = os.path.join(app_ctx.extra['data_dir'], app_ctx.extra['build_file'])
    build_file = BuildFile(build_filename)
    build_ansible_version, ansible_core_version, deps = build_file.parse()
    ansible_core_version_obj = PypiVer(ansible_core_version)
    python_requires = _extract_python_requires(ansible_core_version_obj, deps)

    # TODO: implement --feature-frozen support

    if not str(app_ctx.extra['ansible_version']).startswith(build_ansible_version):
        print(f'{build_filename} is for version {build_ansible_version} but we need'
              f' {app_ctx.extra["ansible_version"].major}'
              f'.{app_ctx.extra["ansible_version"].minor}')
        return 1

    with tempfile.TemporaryDirectory() as tmp_dir:
        download_dir = os.path.join(tmp_dir, 'collections')
        os.mkdir(download_dir, mode=0o700)

        included_versions = asyncio_run(get_collection_versions(deps, app_ctx.galaxy_url))
        asyncio_run(
            download_collections(included_versions, app_ctx.galaxy_url, download_dir,
                                 app_ctx.collection_cache))
        # TODO: PY3.8:
        # collections_to_install = [p for f in os.listdir(download_dir)
        #                           if os.path.isfile(p := os.path.join(download_dir, f))]
        collections_to_install = []
        for collection in os.listdir(download_dir):
            path = os.path.join(download_dir, collection)
            if os.path.isfile(path):
                collections_to_install.append(path)

        collection_dirs = asyncio_run(install_separately(collections_to_install, download_dir))
        asyncio_run(make_collection_dists(app_ctx.extra['sdist_dir'], collection_dirs))

        # Create the ansible package that deps on the collections we just wrote
        package_dir = os.path.join(tmp_dir, f'ansible-{app_ctx.extra["ansible_version"]}')
        os.mkdir(package_dir, mode=0o700)
        ansible_collections_dir = os.path.join(package_dir, 'ansible_collections')
        os.mkdir(ansible_collections_dir, mode=0o700)

        # Construct the list of dependent collection packages
        collection_deps = []
        for collection, version in sorted(included_versions.items()):
            collection_deps.append(f"        '{collection}>={version},<{version.next_major()}'")
        collection_deps_str = '\n' + ',\n'.join(collection_deps)
        write_build_script(app_ctx.extra['ansible_version'], ansible_core_version_obj, package_dir)
        write_python_build_files(app_ctx.extra['ansible_version'], ansible_core_version_obj,
                                 [], collection_deps_str, package_dir,
                                 python_requires=python_requires)

        make_dist(package_dir, app_ctx.extra['sdist_dir'])

    # Write the deps file
    deps_filename = os.path.join(app_ctx.extra['dest_data_dir'], app_ctx.extra['deps_file'])
    deps_file = DepsFile(deps_filename)
    deps_file.write(
        str(app_ctx.extra['ansible_version']),
        str(ansible_core_version_obj),
        {collection: str(version) for collection, version in included_versions.items()},
        python_requires=python_requires)

    return 0
