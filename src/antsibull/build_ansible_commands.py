# Author: Toshio Kuratomi <tkuratom@redhat.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020
"""Build Ansible packages."""

from __future__ import annotations

import asyncio
import datetime
import os
import os.path
import shutil
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp
import asyncio_pool  # type: ignore[import]
from antsibull_core import app_context
from antsibull_core.ansible_core import get_ansible_core
from antsibull_core.collections import install_together
from antsibull_core.dependency_files import BuildFile, DependencyFileData, DepsFile
from antsibull_core.galaxy import CollectionDownloader, GalaxyContext
from antsibull_core.logging import log
from antsibull_core.subprocess_util import async_log_run, log_run
from antsibull_core.yaml import store_yaml_file, store_yaml_stream
from jinja2 import Template
from packaging.version import Version as PypiVer
from semantic_version import Version as SemVer

from antsibull.constants import MINIMUM_ANSIBLE_VERSIONS
from antsibull.python_metadata import BuildMetaMaker, LegacyBuildMetaMaker

from . import __version__ as antsibull_version
from .build_changelog import ReleaseNotes
from .changelog import ChangelogData, get_changelog
from .dep_closure import check_collection_dependencies
from .tagging import get_collections_tags
from .utils.galaxy import create_galaxy_context
from .utils.get_pkg_data import get_antsibull_data
from .versions import (
    feature_freeze_version,
    find_latest_compatible,
    get_latest_ansible_core_version,
    get_version_info,
    load_constraints_if_exists,
)

if TYPE_CHECKING:
    from _typeshed import StrPath


mlog = log.fields(mod=__name__)

TAG_FILE_MESSAGE = """\
# This is a mapping of collections to their git repositories and the git tag
# that corresponds to the version included in this ansible release. A null
# 'tag' field means that a collection's release wasn't tagged.
"""


#
# Common code
#


async def download_collections(
    versions: Mapping[str, SemVer],
    download_dir: str,
    galaxy_context: GalaxyContext,
    collection_cache: str | None = None,
) -> dict[str, str]:
    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        lib_ctx = app_context.lib_ctx.get()
        async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
            downloader = CollectionDownloader(
                aio_session,
                download_dir,
                collection_cache=collection_cache,
                context=galaxy_context,
            )
            for collection_name, version in versions.items():
                requestors[collection_name] = await pool.spawn(
                    downloader.download(collection_name, version)
                )

            values = await asyncio.gather(*requestors.values())
    return dict(zip(versions.keys(), values))


async def _get_ansible_core_path(
    download_dir: StrPath, ansible_core_version: PypiVer | str
) -> Path:
    flog = mlog.fields(func="_get_ansible_core_path")
    async with aiohttp.ClientSession() as aio_session:
        ansible_core_tarball = Path(
            await get_ansible_core(
                aio_session, str(ansible_core_version), str(download_dir)
            )
        )
    await async_log_run(
        ["tar", "-C", download_dir, "-xf", ansible_core_tarball],
        logger=flog,
    )
    return Path(download_dir, ansible_core_tarball.with_suffix("").with_suffix("").name)


#
# Single sdist for ansible
#


def copy_boilerplate_files(package_dir: StrPath) -> None:
    gpl_license = get_antsibull_data("gplv3.txt")
    with open(os.path.join(package_dir, "COPYING"), "wb") as f:
        f.write(gpl_license)

    readme = get_antsibull_data("ansible-readme.rst")
    with open(os.path.join(package_dir, "README.rst"), "wb") as f:
        f.write(readme)

    pyproject_toml = get_antsibull_data("pyproject.toml")
    with open(os.path.join(package_dir, "pyproject.toml"), "wb") as f:
        f.write(pyproject_toml)


def write_manifest(
    package_dir: StrPath,
    release_notes: ReleaseNotes | None = None,
    debian: bool = False,
    tags_file: StrPath | None = None,
) -> None:
    manifest_file = os.path.join(package_dir, "MANIFEST.in")
    with open(manifest_file, "w", encoding="utf-8") as f:
        f.write("include COPYING\n")
        f.write("include README.rst\n")
        f.write("include build-ansible.sh\n")
        if release_notes:
            for changelog in release_notes.changelogs:
                f.write(f"include {changelog.filename}\n")
            f.write(f"include {release_notes.porting_guide.filename}\n")
        if debian:
            f.write("include debian/*\n")
        if tags_file:
            f.write("include tags.yaml\n")
        f.write("recursive-include ansible_collections/ **\n")


def write_release_py(ansible_version: PypiVer, ansible_collections_dir: str) -> None:
    release_filename = os.path.join(ansible_collections_dir, "ansible_release.py")

    release_tmpl = Template(get_antsibull_data("ansible-release_py.j2").decode("utf-8"))
    release_contents = release_tmpl.render(version=ansible_version)

    with open(release_filename, "w", encoding="utf-8") as f:
        f.write(release_contents)


def write_ansible_community_py(
    ansible_version: PypiVer, ansible_collections_dir: str
) -> None:
    release_filename = os.path.join(ansible_collections_dir, "ansible_community.py")

    release_tmpl = Template(
        get_antsibull_data("ansible-community.py.j2").decode("utf-8")
    )
    release_contents = release_tmpl.render(version=ansible_version)

    with open(release_filename, "w", encoding="utf-8") as f:
        f.write(release_contents + "\n")


def copy_tags_file(tags_file: StrPath | None, package_dir: StrPath) -> None:
    if tags_file:
        dest = os.path.join(package_dir, "tags.yaml")
        shutil.copy(tags_file, dest)


def write_python_build_files(
    package_dir: StrPath,
    release_notes: ReleaseNotes | None = None,
    debian: bool = False,
    tags_file: StrPath | None = None,
    stub_setup_py: bool = False,
) -> None:
    copy_boilerplate_files(package_dir)
    copy_tags_file(tags_file, package_dir)
    write_manifest(package_dir, release_notes, debian, tags_file)
    if stub_setup_py:
        Path(package_dir, "setup.py").write_bytes(
            get_antsibull_data("ansible-stub-setup.py")
        )


def write_debian_directory(
    ansible_version: PypiVer,
    ansible_core_version: PypiVer,  # pylint: disable=unused-argument
    package_dir: StrPath,
) -> None:
    debian_dir = os.path.join(package_dir, "debian")
    if not os.path.isdir(debian_dir):
        os.mkdir(debian_dir, mode=0o700)
    debian_files = ("changelog.j2", "control.j2", "copyright", "rules")
    for filename in debian_files:
        # Don't use os.path.join here, the get_data docs say it should be
        # slash-separated.
        src_pkgfile = "debian/" + filename
        data = get_antsibull_data(src_pkgfile).decode("utf-8")

        if filename.endswith(".j2"):
            filename = filename.replace(".j2", "")
            # If the file is a template, send it in vars it might need
            # and update 'data' to be the result.
            tmpl = Template(data)
            data = tmpl.render(
                version=str(ansible_version),
                date=datetime.datetime.utcnow().strftime("%a, %d %b %Y %T +0000"),
                ansible_core_package_name="ansible-core",
            )

        with open(os.path.join(debian_dir, filename), "w", encoding="utf-8") as f:
            f.write(data)


def write_galaxy_requirements(
    filename: str, included_versions: Mapping[str, str]
) -> None:
    galaxy_reqs = []
    for collection, version in sorted(included_versions.items()):
        galaxy_reqs.append(
            {
                "name": collection,
                "version": version,
                "source": "https://galaxy.ansible.com",
            }
        )

    store_yaml_file(
        filename,
        {
            "collections": galaxy_reqs,
        },
    )


def make_dist_with_wheels(ansible_dir: str, dest_dir: str) -> None:
    # TODO: build has an API, but it's quite unstable, so we use the cli for now
    log_run(
        [sys.executable, "-m", "build", "--outdir", dest_dir, ansible_dir],
        logger=mlog.fields(func="make_dist_with_wheels"),
        stderr_loglevel="warning",
    )


def write_build_script(
    ansible_version: PypiVer, ansible_core_version: PypiVer, package_dir: StrPath
) -> None:
    """Write a build-script that tells how to build this tarball."""
    build_ansible_filename = os.path.join(package_dir, "build-ansible.sh")

    build_ansible_tmpl = Template(
        get_antsibull_data("build-ansible.sh.j2").decode("utf-8")
    )
    build_ansible_contents = build_ansible_tmpl.render(
        version=ansible_version,
        ansible_core_version=ansible_core_version,
        antsibull_version=antsibull_version,
    )

    with open(build_ansible_filename, "w", encoding="utf-8") as f:
        f.write(build_ansible_contents)
    os.chmod(build_ansible_filename, mode=0o755)


def write_all_build_files(
    *,
    package_dir: StrPath,
    collections_dir: StrPath,
    ansible_version: PypiVer,
    dependency_data: DependencyFileData,
    ansible_core_version: PypiVer,
    python_requires: str | None = None,
    tags_path: StrPath | None = None,
    debian: bool,
    sdist_src_dir: StrPath | None = None,
    ansible_core_checkout: StrPath,
    release_notes: ReleaseNotes | None = None,
) -> None:
    use_build_meta_maker = (
        ansible_version >= MINIMUM_ANSIBLE_VERSIONS["BUILD_META_MAKER"]
    )
    meta_maker_class: type[BuildMetaMaker | LegacyBuildMetaMaker] = (
        BuildMetaMaker if use_build_meta_maker else LegacyBuildMetaMaker
    )
    build_meta_maker = meta_maker_class(
        package_dir=package_dir,
        collections_dir=collections_dir,
        ansible_version=ansible_version,
        dependency_data=dependency_data,
        ansible_core_version=ansible_core_version,
        ansible_core_checkout=ansible_core_checkout,
        python_requires=python_requires,
    )
    build_meta_maker.write()

    write_build_script(ansible_version, ansible_core_version, package_dir)
    write_python_build_files(
        package_dir, release_notes, debian, tags_path, use_build_meta_maker
    )
    if debian:
        write_debian_directory(ansible_version, ansible_core_version, package_dir)

    if sdist_src_dir:
        shutil.copytree(
            package_dir,
            sdist_src_dir,
            symlinks=True,
            ignore_dangling_symlinks=True,
        )


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
    return version.is_prerelease and pre is not None and pre[0] == "a"


def _extract_python_requires(
    ansible_core_version: PypiVer, deps: dict[str, str]
) -> str:
    python_requires = deps.pop("_python", None)
    if python_requires is not None:
        return python_requires
    if ansible_core_version < PypiVer("2.14.0a"):
        # ansible-core 2.12 and 2.13 support Python 3.8+
        return ">=3.8"
    if ansible_core_version < PypiVer("2.15.0a"):
        # ansible-core 2.14 supports Python 3.9+
        return ">=3.9"
    raise ValueError(
        f"Python requirements for ansible-core {ansible_core_version} should be part of"
        " dependency information"
    )


def prepare_command() -> int:
    app_ctx = app_context.app_ctx.get()
    lib_ctx = app_context.lib_ctx.get()

    build_filename = os.path.join(
        app_ctx.extra["data_dir"], app_ctx.extra["build_file"]
    )
    build_file = BuildFile(build_filename)
    build_ansible_version, ansible_core_version, deps = build_file.parse()
    ansible_core_version_obj = PypiVer(ansible_core_version)
    python_requires = _extract_python_requires(ansible_core_version_obj, deps)

    constraints_filename = os.path.join(
        app_ctx.extra["data_dir"], app_ctx.extra["constraints_file"]
    )
    constraints = load_constraints_if_exists(constraints_filename)

    # If we're building a feature frozen release (betas and rcs) then we need to
    # change the upper version limit to not include new features.
    if app_ctx.extra["feature_frozen"]:
        old_deps, deps = deps, {}
        for collection_name, spec in old_deps.items():
            deps[collection_name] = feature_freeze_version(spec, collection_name)

    galaxy_context = asyncio.run(create_galaxy_context())
    ansible_core_release_infos, collections_to_versions = asyncio.run(
        get_version_info(
            list(deps),
            pypi_server_url=str(lib_ctx.pypi_url),
            galaxy_context=galaxy_context,
        )
    )

    new_ansible_core_version = get_latest_ansible_core_version(
        list(ansible_core_release_infos),
        ansible_core_version_obj,
        pre=_is_alpha(app_ctx.extra["ansible_version"]),
    )
    if new_ansible_core_version:
        ansible_core_version_obj = new_ansible_core_version

    included_versions = find_latest_compatible(
        ansible_core_version_obj,
        collections_to_versions,
        version_specs=deps,
        pre=True,
        prefer_pre=False,
        constraints=constraints,
    )

    if not str(app_ctx.extra["ansible_version"]).startswith(build_ansible_version):
        print(
            f"{build_filename} is for version {build_ansible_version} but we need"
            f' {app_ctx.extra["ansible_version"].major}'
            f'.{app_ctx.extra["ansible_version"].minor}'
        )
        return 1

    dependency_data = DependencyFileData(
        str(app_ctx.extra["ansible_version"]),
        str(ansible_core_version_obj),
        {collection: str(version) for collection, version in included_versions.items()},
    )

    # Get Ansible changelog, add new release
    ansible_changelog = ChangelogData.ansible(
        app_ctx.extra["data_dir"], app_ctx.extra["dest_data_dir"]
    )
    date = datetime.date.today()
    ansible_changelog.add_ansible_release(
        str(app_ctx.extra["ansible_version"]),
        date,
        f"Release Date: {date}"
        f"\n\n"
        f"`Porting Guide <https://docs.ansible.com/ansible/devel/porting_guides.html>`_",
    )
    ansible_changelog.changes.save()

    # Write dependency file
    deps_filename = os.path.join(
        app_ctx.extra["dest_data_dir"], app_ctx.extra["deps_file"]
    )
    deps_file = DepsFile(deps_filename)
    deps_file.write(
        dependency_data.ansible_version,
        dependency_data.ansible_core_version,
        dependency_data.deps,
        python_requires=python_requires,
    )

    # Write tags data
    if app_ctx.extra["tags_file"]:
        tag_data = asyncio.run(
            get_collections_tags(
                app_ctx.extra["dest_data_dir"], app_ctx.extra["deps_file"]
            )
        )
        tags_path = os.path.join(
            app_ctx.extra["dest_data_dir"], app_ctx.extra["tags_file"]
        )
        with open(tags_path, "w", encoding="utf-8") as fp:
            fp.write(TAG_FILE_MESSAGE)
            store_yaml_stream(fp, tag_data)

    # Write Galaxy requirements.yml file
    galaxy_filename = os.path.join(
        app_ctx.extra["dest_data_dir"], app_ctx.extra["galaxy_file"]
    )
    write_galaxy_requirements(galaxy_filename, dependency_data.deps)

    return 0


def rebuild_single_command() -> int:
    app_ctx = app_context.app_ctx.get()
    lib_ctx = app_context.lib_ctx.get()

    deps_filename = os.path.join(app_ctx.extra["data_dir"], app_ctx.extra["deps_file"])
    deps_file = DepsFile(deps_filename)
    dependency_data = deps_file.parse()
    python_requires: str | None
    try:
        python_requires = _extract_python_requires(
            PypiVer(dependency_data.ansible_core_version), dependency_data.deps
        )
    except ValueError:
        python_requires = None

    # Determine included collection versions
    ansible_core_version = PypiVer(dependency_data.ansible_core_version)
    included_versions = {
        collection: SemVer(version)
        for collection, version in dependency_data.deps.items()
    }

    galaxy_context = asyncio.run(create_galaxy_context())

    with tempfile.TemporaryDirectory() as tmp_dir:
        download_dir = os.path.join(tmp_dir, "collections")
        os.mkdir(download_dir, mode=0o700)

        # Download included collections
        asyncio.run(
            download_collections(
                included_versions,
                download_dir=download_dir,
                galaxy_context=galaxy_context,
                collection_cache=lib_ctx.collection_cache,
            )
        )

        # Get Ansible changelog, add new release
        ansible_changelog = ChangelogData.ansible(
            app_ctx.extra["data_dir"], app_ctx.extra["dest_data_dir"]
        )

        # Get changelog and porting guide data
        changelog = get_changelog(
            app_ctx.extra["ansible_version"],
            deps_dir=app_ctx.extra["data_dir"],
            deps_data=[dependency_data],
            collection_cache=lib_ctx.collection_cache,
            ansible_changelog=ansible_changelog,
            galaxy_context=galaxy_context,
        )

        # Create package and collections directories
        package_dir = os.path.join(
            tmp_dir, f'ansible-{app_ctx.extra["ansible_version"]}'
        )
        os.mkdir(package_dir, mode=0o700)
        ansible_collections_dir = os.path.join(package_dir, "ansible_collections")
        os.mkdir(ansible_collections_dir, mode=0o700)

        # Write the ansible release info to the collections dir
        write_release_py(app_ctx.extra["ansible_version"], ansible_collections_dir)

        # Write the ansible-community CLI program
        write_ansible_community_py(
            app_ctx.extra["ansible_version"], ansible_collections_dir
        )

        # Install collections
        collections_to_install = [
            p
            for f in os.listdir(download_dir)
            if os.path.isfile(p := os.path.join(download_dir, f))
        ]

        asyncio.run(install_together(collections_to_install, ansible_collections_dir))

        # Compose and write release notes to destination directory
        release_notes = ReleaseNotes.build(changelog)
        release_notes.write_changelog_to(package_dir)
        release_notes.write_porting_guide_to(package_dir)

        # Write changelog and porting guide also to destination directory
        release_notes.write_changelog_to(app_ctx.extra["dest_data_dir"])
        release_notes.write_porting_guide_to(app_ctx.extra["dest_data_dir"])

        # Write build scripts and files
        tags_path: str | None = None
        if app_ctx.extra["tags_file"]:
            tags_path = os.path.join(
                app_ctx.extra["data_dir"], app_ctx.extra["tags_file"]
            )

        write_all_build_files(
            package_dir=package_dir,
            collections_dir=ansible_collections_dir,
            ansible_version=app_ctx.extra["ansible_version"],
            dependency_data=dependency_data,
            ansible_core_version=ansible_core_version,
            python_requires=python_requires,
            tags_path=tags_path,
            debian=app_ctx.extra["debian"],
            sdist_src_dir=app_ctx.extra.get("sdist_src_dir"),
            ansible_core_checkout=asyncio.run(
                _get_ansible_core_path(tmp_dir, ansible_core_version)
            ),
            release_notes=release_notes,
        )

        # Check dependencies
        dep_errors = check_collection_dependencies(
            os.path.join(package_dir, "ansible_collections")
        )

        if dep_errors:
            is_error = app_ctx.extra["ansible_version"] >= PypiVer("6.3.0")
            warning_error = "ERROR" if is_error else "WARNING"
            print(f"{warning_error}: found collection dependency errors!")
            for error in dep_errors:
                print(f"{warning_error}: {error}")
            if is_error:
                return 3

        # Create source distribution
        make_dist_with_wheels(package_dir, app_ctx.extra["sdist_dir"])

    return 0


def generate_package_files_command() -> int:
    """
    PRIVATE, INTERNAL command to (re)generate package configuration files
    """
    app_ctx = app_context.app_ctx.get()
    package_dir = app_ctx.extra["package_dir"]
    tags_path: str | None = None
    if app_ctx.extra["tags_file"]:
        tags_path = os.path.join(app_ctx.extra["data_dir"], app_ctx.extra["tags_file"])

    deps_filename = os.path.join(app_ctx.extra["data_dir"], app_ctx.extra["deps_file"])
    deps_file = DepsFile(deps_filename)
    dependency_data = deps_file.parse()
    ansible_core_version = PypiVer(dependency_data.ansible_core_version)

    python_requires: str | None
    try:
        python_requires = _extract_python_requires(
            PypiVer(dependency_data.ansible_core_version), dependency_data.deps
        )
    except ValueError:
        python_requires = None

    with tempfile.TemporaryDirectory() as tmp_dir:
        write_all_build_files(
            package_dir=package_dir,
            collections_dir=app_ctx.extra["collections_dir"],
            ansible_version=app_ctx.extra["ansible_version"],
            dependency_data=dependency_data,
            ansible_core_version=ansible_core_version,
            python_requires=python_requires,
            tags_path=tags_path,
            debian=app_ctx.extra["debian"],
            ansible_core_checkout=asyncio.run(
                _get_ansible_core_path(tmp_dir, ansible_core_version)
            ),
        )

    return 0
