# coding: utf-8
# Author: Felix Fontein <tkuratom@redhat.com>
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

import asyncio
from collections import defaultdict
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
from antsibull_changelog.utils import collect_versions

from . import app_context
from .ansible_base import get_ansible_base
from .dependency_files import DepsFile, DependencyFileData
from .galaxy import CollectionDownloader


def read_file(tarball_path: str, matcher: t.Callable[[str], bool]) -> t.Optional[bytes]:
    with tarfile.open(tarball_path, "r:gz") as tar:
        for file in tar:
            if matcher(file.name):
                file_p = tar.extractfile(file)
                if file_p:
                    with file_p:
                        return file_p.read()
    return None


def read_changelog_file(tarball_path: str, is_ansible_base=False) -> t.Optional[bytes]:
    def matcher(filename: str) -> bool:
        if is_ansible_base:
            return filename.endswith('changelogs/changelog.yaml')
        else:
            return filename in ('changelogs/changelog.yaml', 'changelog.yaml')

    return read_file(tarball_path, matcher)


def get_porting_guide_filename(version: PypiVer):
    return f"docs/docsite/rst/porting_guides/porting_guide_base_{version.major}.{version.minor}.rst"


def read_porting_guide_file(tarball_path: str, version: PypiVer) -> t.Optional[bytes]:
    filename = get_porting_guide_filename(version)
    return read_file(tarball_path, lambda fn: fn == filename)


class CollectionChangelogCollector:
    collection: str
    versions: t.List[SemVer]
    earliest: SemVer
    latest: SemVer

    config: ChangelogConfig

    changelog: t.Optional[ChangesData]
    changelog_generator: t.Optional[ChangelogGenerator]

    def __init__(self, collection: str, versions: t.ValuesView[str]):
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

        self.changelog = None
        self.changelog_generator = None

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

        changelog = ChangesData.concatenate(changelogs)
        flatmap = True  # TODO

        self.changelog = changelog
        self.changelog_generator = ChangelogGenerator(
            self.config, changelog, plugins=None, fragments=None, flatmap=flatmap)


class AnsibleBaseChangelogCollector:
    versions: t.List[PypiVer]
    earliest: PypiVer
    latest: PypiVer

    config: ChangelogConfig

    changelog: t.Optional[ChangesData]
    changelog_generator: t.Optional[ChangelogGenerator]

    porting_guide: t.Optional[bytes]

    def __init__(self, versions: t.ValuesView[str]):
        self.versions = sorted(PypiVer(version) for version in versions)
        self.earliest = self.versions[0]
        self.latest = self.versions[-1]

        paths = PathsConfig.force_ansible('')
        collection_details = CollectionDetails(paths)
        self.config = ChangelogConfig.default(paths, collection_details)

        self.changelog = None
        self.changelog_generator = None

        self.porting_guide = None

    async def _get_files(self, version: PypiVer,
                         base_downloader: t.Callable[[str], t.Awaitable[str]]
                         ) -> t.Tuple[t.Optional[ChangesData], t.Optional[bytes]]:
        path = await base_downloader(str(version))
        if os.path.isdir(path):
            pg_path, pg_filename = os.path.split(get_porting_guide_filename(version))
            changelog = None
            porting_guide = None
            for root, _, files in os.walk(path):
                if 'changelog.yaml' in files:
                    with open(os.path.join(root, 'changelog.yaml'), 'rb') as f:
                        changelog = f.read()
                    changelog_data = yaml.load(changelog, Loader=yaml.SafeLoader)
                    changelog = ChangesData(self.config, '/', changelog_data)
                if pg_filename in files:
                    if os.path.join(path, pg_path) == root:
                        with open(os.path.join(path, pg_path), 'rb') as f:
                            porting_guide = f.read()
            return changelog_data, porting_guide
        if os.path.isfile(path) and path.endswith('.tar.gz'):
            changelog = read_changelog_file(path, is_ansible_base=True)
            porting_guide = read_porting_guide_file(path, version)
            if changelog is None:
                return (None, porting_guide)
            changelog_data = yaml.load(changelog, Loader=yaml.SafeLoader)
            return (ChangesData(self.config, '/', changelog_data), porting_guide)
        return None, None

    def _set_changelog(self, changelog: ChangesData):
        self.changelog = changelog
        self.changelog_generator = ChangelogGenerator(
            self.config, changelog, plugins=None, fragments=None, flatmap=True)

    async def download(self, base_downloader: t.Callable[[str], t.Awaitable[str]]):
        changelog, porting_guide = await self._get_files(self.latest, base_downloader)
        if porting_guide:
            self.porting_guide = porting_guide
        if changelog is None:
            return

        changelog.prune_versions(versions_after=None, versions_until=str(self.latest))

        changelogs = [changelog]
        ancestor = changelog.ancestor
        while ancestor is not None:
            ancestor_ver = PypiVer(ancestor)
            if ancestor_ver < self.earliest:
                break
            changelog, _ = await self._get_files(ancestor_ver, base_downloader)
            if changelog is None:
                break
            changelog.prune_versions(versions_after=None, versions_until=ancestor)
            changelogs.append(changelog)
            ancestor = changelog.ancestor

        self._set_changelog(ChangesData.concatenate(changelogs))

    async def download_github(self, aio_session: 'aiohttp.client.ClientSession'):
        branch_url = (f"https://raw.githubusercontent.com/ansible/ansible/"
                      f"stable-{self.latest.major}.{self.latest.minor}")

        # Changelog
        query_url = f"{branch_url}/changelogs/changelog.yaml"
        async with aio_session.get(query_url) as response:
            changelog = await response.read()
        changelog_data = yaml.load(changelog, Loader=yaml.SafeLoader)
        self._set_changelog(ChangesData(self.config, '/', changelog_data))

        # Porting Guide
        query_url = f"{branch_url}/{get_porting_guide_filename(self.latest)}"
        async with aio_session.get(query_url) as response:
            self.porting_guide = await response.read()


async def collect_changelogs(collectors: t.List[CollectionChangelogCollector],
                             base_collector: AnsibleBaseChangelogCollector,
                             collection_cache: t.Optional[str]):
    lib_ctx = app_context.lib_ctx.get()
    with tempfile.TemporaryDirectory() as tmp_dir:
        async with aiohttp.ClientSession() as aio_session:
            async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
                downloader = CollectionDownloader(aio_session, tmp_dir,
                                                  collection_cache=collection_cache)

                async def base_downloader(version):
                    return await get_ansible_base(aio_session, version, tmp_dir)

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


class ChangelogEntry:
    version: PypiVer
    version_str: str

    prev_version: t.Optional[PypiVer]
    base_versions: t.Dict[PypiVer, str]
    versions_per_collection: t.Dict[str, t.Dict[PypiVer, str]]

    base_collector: AnsibleBaseChangelogCollector
    ansible_changelog: ChangesData
    ansible_changelog_generator: ChangelogGenerator
    collectors: t.List[CollectionChangelogCollector]

    ansible_base_version: str
    prev_ansible_base_version: t.Optional[str]

    removed_collections: t.List[t.Tuple[CollectionChangelogCollector, str]]
    added_collections: t.List[t.Tuple[CollectionChangelogCollector, str]]
    unchanged_collections: t.List[t.Tuple[CollectionChangelogCollector, str]]
    changed_collections: t.List[t.Tuple[CollectionChangelogCollector, str, t.Optional[str]]]

    def __init__(self, version: PypiVer, version_str: str,
                 prev_version: t.Optional[PypiVer],
                 base_versions: t.Dict[PypiVer, str],
                 versions_per_collection: t.Dict[str, t.Dict[PypiVer, str]],
                 base_collector: AnsibleBaseChangelogCollector,
                 ansible_changelog: ChangesData,
                 ansible_changelog_generator: ChangelogGenerator,
                 collectors: t.List[CollectionChangelogCollector]):
        self.version = version
        self.version_str = version_str
        self.prev_version = prev_version
        self.base_versions = base_versions
        self.versions_per_collection = versions_per_collection
        self.base_collector = base_collector
        self.ansible_changelog = ansible_changelog
        self.ansible_changelog_generator = ansible_changelog_generator
        self.collectors = collectors

        self.ansible_base_version = base_versions[version]
        self.prev_ansible_base_version = base_versions.get(prev_version) if prev_version else None

        self.removed_collections = []
        self.added_collections = []
        self.unchanged_collections = []
        self.changed_collections = []
        for collector in collectors:
            if version not in versions_per_collection[collector.collection]:
                if prev_version and prev_version in versions_per_collection[collector.collection]:
                    self.removed_collections.append((
                        collector, versions_per_collection[collector.collection][prev_version]))

                continue

            collection_version: str = versions_per_collection[collector.collection][version]

            prev_collection_version: t.Optional[str] = (
                versions_per_collection[collector.collection].get(prev_version)
                if prev_version else None
            )
            if prev_version:
                if not prev_collection_version:
                    self.added_collections.append((collector, collection_version))
                elif prev_collection_version == collection_version:
                    self.unchanged_collections.append((collector, collection_version))
                    continue

            self.changed_collections.append((
                collector, collection_version, prev_collection_version))


class Changelog:
    ansible_version: PypiVer
    entries: t.List[ChangelogEntry]
    base_collector: AnsibleBaseChangelogCollector
    collection_collectors: t.List[CollectionChangelogCollector]

    def __init__(self,
                 ansible_version: PypiVer,
                 entries: t.List[ChangelogEntry],
                 base_collector: AnsibleBaseChangelogCollector,
                 collection_collectors: t.List[CollectionChangelogCollector]):
        self.ansible_version = ansible_version
        self.entries = entries
        self.base_collector = base_collector
        self.collection_collectors = collection_collectors


def get_changelog(
        ansible_version: PypiVer,
        deps_dir: t.Optional[str],
        deps_data: t.Optional[t.List[DependencyFileData]] = None,
        collection_cache: t.Optional[str] = None,
        ) -> Changelog:
    dependencies: t.Dict[str, DependencyFileData] = {}

    ansible_paths = PathsConfig.force_ansible('')
    ansible_changelog_config = ChangelogConfig.default(
        ansible_paths, CollectionDetails(ansible_paths), 'Ansible')
    # TODO: adjust the following lines once Ansible switches to semantic versioning
    ansible_changelog_config.use_semantic_versioning = False
    ansible_changelog_config.release_tag_re = r'''(v(?:[\d.ab\-]|rc)+)'''
    ansible_changelog_config.pre_release_tag_re = r'''(?P<pre_release>(?:[ab]|rc)+\d*)$'''
    ansible_changelog = ChangesData(ansible_changelog_config, '')  # empty changelog

    if deps_dir is not None:
        for path in glob.glob(os.path.join(deps_dir, '*.deps'), recursive=False):
            deps_file = DepsFile(path)
            deps = deps_file.parse()
            version = PypiVer(deps.ansible_version)
            if version > ansible_version:
                print(f"Ignoring {path}, since {deps.ansible_version}"
                      f" is newer than {ansible_version}")
                continue
            dependencies[deps.ansible_version] = deps
        ansible_changelog = ChangesData(
            ansible_changelog_config, os.path.join(deps_dir, 'changelog.yaml'))
    if deps_data:
        for deps in deps_data:
            dependencies[deps.ansible_version] = deps

    ansible_changelog_generator = ChangelogGenerator(
        ansible_changelog_config, ansible_changelog, plugins=None, fragments=None, flatmap=True)

    base_versions: t.Dict[PypiVer, str] = dict()
    versions: t.Dict[str, t.Tuple[PypiVer, DependencyFileData]] = dict()
    versions_per_collection: t.Dict[str, t.Dict[PypiVer, str]] = defaultdict(dict)
    for deps in dependencies.values():
        version = PypiVer(deps.ansible_version)
        versions[deps.ansible_version] = (version, deps)
        base_versions[version] = deps.ansible_base_version
        for collection_name, collection_version in deps.deps.items():
            versions_per_collection[collection_name][version] = collection_version

    base_collector = AnsibleBaseChangelogCollector(base_versions.values())
    collectors = [
        CollectionChangelogCollector(collection, versions_per_collection[collection].values())
        for collection in sorted(versions_per_collection.keys())
    ]
    asyncio.run(collect_changelogs(collectors, base_collector, collection_cache))

    changelog = []

    sorted_versions = collect_versions(versions, ansible_changelog_config)
    for index, (version_str, _) in enumerate(sorted_versions):
        version, deps = versions[version_str]
        prev_version = None
        if index + 1 < len(sorted_versions):
            prev_version = versions[sorted_versions[index + 1][0]][0]

        changelog.append(ChangelogEntry(
            version,
            version_str,
            prev_version,
            base_versions,
            versions_per_collection,
            base_collector,
            ansible_changelog,
            ansible_changelog_generator,
            collectors))

    return Changelog(ansible_version, changelog, base_collector, collectors)
