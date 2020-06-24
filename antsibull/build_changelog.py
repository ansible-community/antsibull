# coding: utf-8
# Author: Felix Fontein <tkuratom@redhat.com>
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

import asyncio
from collections import defaultdict
from functools import partial
import glob
import os
import os.path
import tarfile
import tempfile
import typing as t

import aiohttp
import asyncio_pool
import yaml
from packaging.version import Version as PypiVer
from semantic_version import Version as SemVer

from antsibull_changelog.config import PathsConfig, CollectionDetails, ChangelogConfig
from antsibull_changelog.changes import ChangesData
from antsibull_changelog.changelog_generator import ChangelogGenerator
from antsibull_changelog.rst import RstBuilder

from .ansible_base import get_ansible_base
from .constants import THREAD_MAX
from .dependency_files import DepsFile, DependencyFileData
from .galaxy import CollectionDownloader


async def download_collections(deps, download_dir, collection_cache=None):
    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        async with asyncio_pool.AioPool(size=THREAD_MAX) as pool:
            downloader = CollectionDownloader(aio_session, download_dir,
                                              collection_cache=collection_cache)
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


def read_changelog_file(tarball_path: str, is_ansible_base=False) -> t.Optional[bytes]:
    with tarfile.open(tarball_path, "r:gz") as tar:
        for file in tar:
            if is_ansible_base:
                found = file.name.endswith('changelogs/changelog.yaml')
            else:
                found = file.name in ('changelogs/changelog.yaml', 'changelog.yaml')
            if found:
                with tar.extractfile(file) as file_p:
                    return file_p.read()
    return None


class CollectionChangelogCollector:
    collection: str
    versions: t.List[SemVer]
    earliest: SemVer
    latest: SemVer

    changelog: t.Optional[ChangesData]

    def __init__(self, collection: str, versions: t.List[str]):
        self.collection = collection
        self.versions = sorted(SemVer(version) for version in versions)
        self.earliest = self.versions[0]
        self.latest = self.versions[-1]

        paths = PathsConfig.force_collection('')
        collection_details = CollectionDetails(paths)
        collection_details.namespace, collection_details.name = collection.split('.', 1)
        collection_details.version = str(self.latest)
        collection_details.flatmap = False  # TODO!
        self.config = ChangelogConfig.default(paths, collection_details)

        self.changelog_data = None
        self.changelog = None

    async def _get_changelog(self, version: SemVer,
                             collection_downloader: CollectionDownloader
                             ) -> t.Optional[ChangesData]:
        path = await collection_downloader.download(self.collection, version)
        changelog = read_changelog_file(path)
        if changelog is None:
            return None
        changelog_data = yaml.load(changelog, Loader=yaml.SafeLoader)
        return ChangesData(self.config, '/', changelog_data)

    async def download(self, collection_downloader: CollectionDownloader):
        changelog = await self._get_changelog(self.latest, collection_downloader)
        if changelog is None:
            return

        changelog.prune_versions(versions_after=None, versions_until=str(self.latest))

        changelogs = [changelog]
        ancestor = changelog.ancestor
        while ancestor is not None:
            ancestor_ver = SemVer(ancestor)
            if ancestor_ver < self.earliest:
                break
            changelog = await self._get_changelog(ancestor_ver, collection_downloader)
            if changelog is None:
                break
            changelog.prune_versions(versions_after=None, versions_until=ancestor)
            changelogs.append(changelog)
            ancestor = changelog.ancestor

        self.changelog = ChangesData.concatenate(changelogs)


class AnsibleBaseChangelogCollector:
    versions: t.List[PypiVer]
    earliest: PypiVer
    latest: PypiVer

    changelog: t.Optional[ChangesData]

    def __init__(self, versions: t.List[str]):
        self.versions = sorted(PypiVer(version) for version in versions)
        self.earliest = self.versions[0]
        self.latest = self.versions[-1]

        paths = PathsConfig.force_ansible('')
        collection_details = CollectionDetails(paths)
        self.config = ChangelogConfig.default(paths, collection_details)

        self.changelog_data = None
        self.changelog = None

    async def _get_changelog(self, version: PypiVer,
                             base_downloader: t.Callable[[str], str]
                             ) -> t.Optional[ChangesData]:
        path = await base_downloader(str(version))
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                if 'changelog.yaml' in files:
                    with open(os.path.join(root, 'changelog.yaml'), 'rb') as f:
                        changelog = f.read()
                    changelog_data = yaml.load(changelog, Loader=yaml.SafeLoader)
                    return ChangesData(self.config, '/', changelog_data)
        if os.path.isfile(path) and path.endswith('.tar.gz'):
            changelog = read_changelog_file(path, x=True)
            if changelog is None:
                return None
            changelog_data = yaml.load(changelog, Loader=yaml.SafeLoader)
            return ChangesData(self.config, '/', changelog_data)
        return None

    async def download(self, base_downloader: t.Callable[[str], str]):
        changelog = await self._get_changelog(self.latest, base_downloader)
        if changelog is None:
            return

        changelog.prune_versions(versions_after=None, versions_until=str(self.latest))

        changelogs = [changelog]
        ancestor = changelog.ancestor
        while ancestor is not None:
            ancestor_ver = PypiVer(ancestor)
            if ancestor_ver < self.earliest:
                break
            changelog = await self._get_changelog(ancestor_ver, base_downloader)
            if changelog is None:
                break
            changelog.prune_versions(versions_after=None, versions_until=ancestor)
            changelogs.append(changelog)
            ancestor = changelog.ancestor

        self.changelog = ChangesData.concatenate(changelogs)

    async def download_github(self, aio_session: 'aiohttp.client.ClientSession'):
        query_url = (f"https://raw.githubusercontent.com/ansible/ansible/"
                     f"stable-{self.latest.major}.{self.latest.minor}/changelogs/changelog.yaml")
        async with aio_session.get(query_url) as response:
            changelog = await response.read()
        changelog_data = yaml.load(changelog, Loader=yaml.SafeLoader)
        self.changelog = ChangesData(self.config, '/', changelog_data)


async def collect_changelogs(collectors: t.List[CollectionChangelogCollector],
                             base_collector: AnsibleBaseChangelogCollector,
                             collection_cache: t.Optional[str]):
    with tempfile.TemporaryDirectory() as tmp_dir:
        async with aiohttp.ClientSession() as aio_session:
            async with asyncio_pool.AioPool(size=THREAD_MAX) as pool:
                downloader = CollectionDownloader(aio_session, tmp_dir,
                                                  collection_cache=collection_cache)
                base_downloader = partial(get_ansible_base, aio_session, tmpdir=tmp_dir)

                requestors = [
                    await pool.spawn(collector.download(downloader)) for collector in collectors
                ]
                if False:  # TODO: make this depend on version or something else...
                    requestors.append(
                        await pool.spawn(base_collector.download(base_downloader)))
                else:
                    requestors.append(
                        await pool.spawn(base_collector.download_github(aio_session)))
                await asyncio.gather(*requestors)


def append_changelog(builder: RstBuilder, version: PypiVer, version_str: str,
                     prev_version: t.Optional[PypiVer],
                     base_versions: t.Dict[PypiVer, str],
                     versions_per_collection: t.Dict[str, t.Dict[PypiVer, str]],
                     base_collector: AnsibleBaseChangelogCollector,
                     collectors: t.List[CollectionChangelogCollector],
                     ):
    builder.add_section('v{0}'.format(version_str), 0)

    if base_collector.changelog:
        builder.add_section('Ansible Base', 1)
        builder.add_raw_rst('.. contents::')
        builder.add_raw_rst('  :local:')
        builder.add_raw_rst('  :depth: 5\n')

        base_version: str = base_versions[version]

        prev_base_version = base_versions.get(prev_version)

        generator = ChangelogGenerator(
            base_collector.config, base_collector.changelog,
            plugins=None, fragments=None, flatmap=True)
        generator.generate_to(
            builder, 1, squash=True,
            after_version=prev_base_version,
            until_version=base_version)

    for collector in collectors:
        if version not in versions_per_collection[collector.collection]:
            print(f"WARNING: {collector.collection} is not included in Ansible {version}")

            if prev_version and prev_version in versions_per_collection[collector.collection]:
                builder.add_section(f"{collector.collection.title()} Was Removed", 1)
                builder.add_raw_rst(f"The collection {collector.collection} was removed "
                                    f"in Ansible {version}.\n")

            continue

        collection_version: str = versions_per_collection[collector.collection][version]

        prev_collection_version: t.Optional[str] = None
        if prev_version and prev_version not in versions_per_collection[collector.collection]:
            builder.add_section(f"{collector.collection.title()} (New)", 1)
            builder.add_raw_rst(f"The collection {collector.collection} was "
                                f"added in Ansible {version}.\n")
        else:
            builder.add_section(collector.collection.title(), 1)
            builder.add_raw_rst(f"Ansible {version} contains {collector.collection} "
                                f"version {collection_version}.")
            if prev_version:
                prev_collection_version = (
                    versions_per_collection[collector.collection][prev_version]
                )
                if prev_collection_version == collection_version:
                    builder.add_raw_rst("This is the same version as in the previous "
                                        "Ansible release.\n")
                    continue
                else:
                    builder.add_raw_rst(f"This is a newer version than version "
                                        f"{prev_collection_version} contained in the "
                                        f"previous Ansible release.\n")
            else:
                builder.add_raw_rst('')

        if not collector.changelog:
            builder.add_raw_rst(f"Unfortunately, {collector.collection} has no Ansible "
                                f"compatible changelog.\n")
            # TODO: add link to collection's changelog
            continue

        # TODO: actually check that there are no release information for this version range!
        if not collector.changelog.releases:
            builder.add_raw_rst("There are no changes recorded in the changelog, or "
                                "the collection did not have a changelog in this version.\n")
            continue

        flatmap = True  # TODO
        generator = ChangelogGenerator(
            collector.config, collector.changelog,
            plugins=None, fragments=None, flatmap=flatmap)

        builder.add_raw_rst('.. contents::')
        builder.add_raw_rst('  :local:')
        builder.add_raw_rst('  :depth: 5\n')

        generator.generate_to(
            builder, 1, squash=True,
            after_version=prev_collection_version,
            until_version=collection_version)


def build_changelog(args):
    # args.dest_dir

    versions: t.List[t.Tuple[str, PypiVer, DependencyFileData]] = []

    acd_version = args.acd_version
    base_versions: t.Dict[PypiVer, str] = dict()
    versions_per_collection: t.Dict[str, t.Dict[PypiVer, str]] = defaultdict(dict)
    for path in glob.glob(os.path.join(args.deps_dir, '*.deps'), recursive=False):
        deps_file = DepsFile(path)
        deps = deps_file.parse()
        version = PypiVer(deps.ansible_version)
        if version > acd_version:
            print(f"Ignoring {path}, since {deps.ansible_version} is newer than {acd_version}")
        versions.append((deps.ansible_version, version, deps))
        base_versions[version] = deps.ansible_base_version
        for collection_name, collection_version in deps.deps.items():
            versions_per_collection[collection_name][version] = collection_version

    versions.sort(key=lambda tuple: tuple[1])

    base_collector = AnsibleBaseChangelogCollector(base_versions.values())
    collectors = [
        CollectionChangelogCollector(collection, versions_per_collection[collection].values())
        for collection in sorted(versions_per_collection.keys())
    ]
    asyncio.run(collect_changelogs(collectors, base_collector, args.collection_cache))

    builder = RstBuilder()
    builder.set_title(f"Ansible {acd_version.major}.{acd_version.minor} Release Notes")
    builder.add_raw_rst('.. contents::\n  :local:\n  :depth: 2\n')

    for index, (version_str, version, deps) in enumerate(reversed(versions)):
        if index + 1 < len(versions):
            prev_version = versions[len(versions) - index - 2][1]
        else:
            prev_version = None

        append_changelog(
            builder, version, version_str, prev_version,
            base_versions, versions_per_collection,
            base_collector, collectors)

    path = os.path.join(args.dest_dir, f"CHANGELOG-v{acd_version.major}.{acd_version.minor}.rst")
    with open(path, 'wb') as changelog_fd:
        changelog_fd.write(builder.generate().encode('utf-8'))
