# Author: Felix Fontein <felix@fontein.de>
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020
"""Changelog handling and processing code."""

import asyncio
from collections import defaultdict
import datetime
import glob
import os
import os.path
import tarfile
import tempfile
import typing as t

import aiohttp
import asyncio_pool  # type: ignore[import]
from packaging.version import Version as PypiVer
from semantic_version import Version as SemVer

from antsibull_changelog.config import PathsConfig, CollectionDetails, ChangelogConfig
from antsibull_changelog.changes import add_release, ChangesData
from antsibull_changelog.changelog_generator import ChangelogGenerator
from antsibull_changelog.utils import collect_versions

from antsibull_core import app_context
from antsibull_core.ansible_core import get_ansible_core
from antsibull_core.compat import asyncio_run
from antsibull_core.dependency_files import DepsFile, DependencyFileData
from antsibull_core.galaxy import CollectionDownloader
from antsibull_core.yaml import load_yaml_bytes, load_yaml_file


class ChangelogData:
    '''
    Data for a single changelog (for a collection, for ansible-core, for Ansible)
    '''

    paths: PathsConfig
    config: ChangelogConfig
    changes: ChangesData
    generator: ChangelogGenerator
    generator_flatmap: bool

    def __init__(self, paths: PathsConfig, config: ChangelogConfig,
                 changes: ChangesData, flatmap: bool = False):
        self.paths = paths
        self.config = config
        self.changes = changes
        self.generator_flatmap = flatmap
        self.generator = ChangelogGenerator(
            self.config, self.changes, plugins=None, fragments=None, flatmap=flatmap)

    @classmethod
    def collection(cls, collection_name: str, version: str,
                   changelog_data: t.Optional[t.Any] = None) -> 'ChangelogData':
        paths = PathsConfig.force_collection('')
        collection_details = CollectionDetails(paths)
        collection_details.namespace, collection_details.name = collection_name.split('.', 1)
        collection_details.version = version
        collection_details.flatmap = False  # TODO!
        config = ChangelogConfig.default(paths, collection_details)
        return cls(paths,
                   config,
                   ChangesData(config, '', changelog_data),
                   flatmap=True)  # TODO!

    @classmethod
    def ansible_core(cls, changelog_data: t.Optional[t.Any] = None) -> 'ChangelogData':
        paths = PathsConfig.force_ansible('')
        collection_details = CollectionDetails(paths)
        config = ChangelogConfig.default(paths, collection_details)
        return cls(paths, config, ChangesData(config, '', changelog_data), flatmap=False)

    @classmethod
    def ansible(cls, directory: t.Optional[str],
                output_directory: t.Optional[str] = None) -> 'ChangelogData':
        paths = PathsConfig.force_ansible('')

        config = ChangelogConfig.default(paths, CollectionDetails(paths), 'Ansible')
        # TODO: adjust the following lines once Ansible switches to semantic versioning
        config.use_semantic_versioning = False
        config.release_tag_re = r'''(v(?:[\d.ab\-]|rc)+)'''
        config.pre_release_tag_re = r'''(?P<pre_release>(?:[ab]|rc)+\d*)$'''

        changelog_path = ''
        if directory is not None:
            changelog_path = os.path.join(directory, 'changelog.yaml')
        changes = ChangesData(config, changelog_path)
        if output_directory is not None:
            changes.path = os.path.join(output_directory, 'changelog.yaml')
        return cls(paths, config, changes, flatmap=True)

    @classmethod
    def concatenate(cls, changelogs: t.List['ChangelogData']) -> 'ChangelogData':
        return cls(
            changelogs[0].paths,
            changelogs[0].config,
            ChangesData.concatenate([changelog.changes for changelog in changelogs]),
            flatmap=changelogs[0].generator_flatmap)

    def add_ansible_release(self, version: str, date: datetime.date, release_summary: str) -> None:
        add_release(self.config, self.changes, [], [], version,
                    codename=None, date=date, update_existing=True,
                    show_release_summary_warning=False)
        release_date = self.changes.releases[version]
        if 'changes' not in release_date:
            release_date['changes'] = {}
        release_date['changes']['release_summary'] = release_summary


def read_file(tarball_path: str, matcher: t.Callable[[str], bool]) -> t.Optional[bytes]:
    with tarfile.open(tarball_path, "r:gz") as tar:
        for file in tar:
            if matcher(file.name):
                file_p = tar.extractfile(file)
                if file_p:
                    with file_p:
                        return file_p.read()
    return None


def read_changelog_file(tarball_path: str, is_ansible_core=False) -> t.Optional[bytes]:
    def matcher(filename: str) -> bool:
        if is_ansible_core:
            return filename.endswith('changelogs/changelog.yaml')
        return filename in ('changelogs/changelog.yaml', 'changelog.yaml')

    return read_file(tarball_path, matcher)


def get_porting_guide_filename(version: PypiVer):
    if version.major == 2 and version.minor == 10:
        basename = 'porting_guide_base'
    else:
        basename = 'porting_guide_core'
    return f"docs/docsite/rst/porting_guides/{basename}_{version.major}.{version.minor}.rst"


def read_porting_guide_file(tarball_path: str, version: PypiVer) -> t.Optional[bytes]:
    filename = get_porting_guide_filename(version)
    return read_file(tarball_path, lambda fn: fn == filename)


class CollectionChangelogCollector:
    collection: str
    versions: t.List[SemVer]
    earliest: SemVer
    latest: SemVer

    changelog: t.Optional[ChangelogData]

    def __init__(self, collection: str, versions: t.ValuesView[str]):
        self.collection = collection
        self.versions = sorted(SemVer(version) for version in versions)
        self.earliest = self.versions[0]
        self.latest = self.versions[-1]
        self.changelog = None

    async def _get_changelog(self, version: SemVer,
                             collection_downloader: CollectionDownloader
                             ) -> t.Optional[ChangelogData]:
        path = await collection_downloader.download(self.collection, version)
        changelog_bytes = read_changelog_file(path)
        if changelog_bytes is None:
            return None
        changelog_data = load_yaml_bytes(changelog_bytes)
        return ChangelogData.collection(self.collection, str(version), changelog_data)

    async def _download_changelog_stream(self, start_version: SemVer,
                                         collection_downloader: CollectionDownloader
                                         ) -> t.Optional[ChangelogData]:
        changelog = await self._get_changelog(start_version, collection_downloader)
        if changelog is None:
            return None

        changelog.changes.prune_versions(versions_after=None, versions_until=str(start_version))
        changelogs = [changelog]
        ancestor = changelog.changes.ancestor
        while ancestor is not None:
            ancestor_ver = SemVer(ancestor)
            if ancestor_ver < self.earliest:
                break
            changelog = await self._get_changelog(ancestor_ver, collection_downloader)
            if changelog is None:
                break
            changelog.changes.prune_versions(versions_after=None, versions_until=ancestor)
            changelogs.append(changelog)
            ancestor = changelog.changes.ancestor

        return ChangelogData.concatenate(changelogs)

    async def download(self, collection_downloader: CollectionDownloader):
        missing_versions = set(self.versions)

        while missing_versions:
            missing_version = max(missing_versions)

            # Try to get hold of changelog for this version
            changelog = await self._download_changelog_stream(
                missing_version, collection_downloader)
            if changelog:
                current_changelog = self.changelog
                if current_changelog is None:
                    # If we didn't have a changelog so far, start with it
                    self.changelog = changelog
                    missing_versions -= {SemVer(version) for version in changelog.changes.releases}
                else:
                    # Insert entries from changelog into combined changelog that are missing there
                    for version, entry in changelog.changes.releases.items():
                        sem_version = SemVer(version)
                        if sem_version in missing_versions:
                            current_changelog.changes.releases[version] = entry
                            missing_versions.remove(sem_version)

            # Make sure that this version isn't checked again
            missing_versions -= {missing_version}


class AnsibleCoreChangelogCollector:
    versions: t.List[PypiVer]
    earliest: PypiVer
    latest: PypiVer

    changelog: t.Optional[ChangelogData]

    porting_guide: t.Optional[bytes]

    def __init__(self, versions: t.ValuesView[str]):
        self.versions = sorted(PypiVer(version) for version in versions)
        self.earliest = self.versions[0]
        self.latest = self.versions[-1]
        self.changelog = None
        self.porting_guide = None

    @staticmethod
    async def _get_changelog_file(version: PypiVer,
                                  core_downloader: t.Callable[[str], t.Awaitable[str]]
                                  ) -> t.Optional[ChangelogData]:
        path = await core_downloader(str(version))
        if os.path.isdir(path):
            changelog: t.Optional[ChangelogData] = None
            for root, dummy, files in os.walk(path):
                if 'changelog.yaml' in files:
                    with open(os.path.join(root, 'changelog.yaml'), 'rb') as f:
                        changelog_bytes = f.read()
                    changelog_data = load_yaml_bytes(changelog_bytes)
                    changelog = ChangelogData.ansible_core(changelog_data)
            return changelog
        if os.path.isfile(path) and path.endswith('.tar.gz'):
            maybe_changelog_bytes = read_changelog_file(path, is_ansible_core=True)
            if maybe_changelog_bytes is None:
                return None
            changelog_data = load_yaml_bytes(maybe_changelog_bytes)
            return ChangelogData.ansible_core(changelog_data)
        return None

    async def download_changelog(self, core_downloader: t.Callable[[str], t.Awaitable[str]]):
        changelog = await self._get_changelog_file(self.latest, core_downloader)
        if changelog is None:
            return

        changelog.changes.prune_versions(versions_after=None, versions_until=str(self.latest))

        changelogs = [changelog]
        ancestor = changelog.changes.ancestor
        while ancestor is not None:
            ancestor_ver = PypiVer(ancestor)
            if ancestor_ver < self.earliest:
                break
            changelog = await self._get_changelog_file(ancestor_ver, core_downloader)
            if changelog is None:
                break
            changelog.changes.prune_versions(versions_after=None, versions_until=ancestor)
            changelogs.append(changelog)
            ancestor = changelog.changes.ancestor

        self.changelog = ChangelogData.concatenate(changelogs)

    async def download_porting_guide(self, aio_session: 'aiohttp.client.ClientSession'):
        branch_url = 'https://raw.githubusercontent.com/ansible/ansible/devel'

        query_url = f"{branch_url}/{get_porting_guide_filename(self.latest)}"
        async with aio_session.get(query_url) as response:
            self.porting_guide = await response.read()


async def collect_changelogs(collectors: t.List[CollectionChangelogCollector],
                             core_collector: AnsibleCoreChangelogCollector,
                             collection_cache: t.Optional[str]):
    lib_ctx = app_context.lib_ctx.get()
    with tempfile.TemporaryDirectory() as tmp_dir:
        async with aiohttp.ClientSession() as aio_session:
            async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
                downloader = CollectionDownloader(aio_session, tmp_dir,
                                                  collection_cache=collection_cache)

                async def core_downloader(version):
                    return await get_ansible_core(aio_session, version, tmp_dir)

                requestors = [
                    await pool.spawn(collector.download(downloader)) for collector in collectors
                ]
                requestors.append(
                    await pool.spawn(core_collector.download_changelog(core_downloader)))
                requestors.append(
                    await pool.spawn(core_collector.download_porting_guide(aio_session)))
                await asyncio.gather(*requestors)


class ChangelogEntry:
    version: PypiVer
    version_str: str
    is_ancestor: bool

    prev_version: t.Optional[PypiVer]
    core_versions: t.Dict[PypiVer, str]
    versions_per_collection: t.Dict[str, t.Dict[PypiVer, str]]

    core_collector: AnsibleCoreChangelogCollector
    ansible_changelog: ChangelogData
    collectors: t.List[CollectionChangelogCollector]

    ansible_core_version: str
    prev_ansible_core_version: t.Optional[str]

    removed_collections: t.List[t.Tuple[CollectionChangelogCollector, str]]
    added_collections: t.List[t.Tuple[CollectionChangelogCollector, str]]
    unchanged_collections: t.List[t.Tuple[CollectionChangelogCollector, str]]
    changed_collections: t.List[t.Tuple[CollectionChangelogCollector, str, t.Optional[str], bool]]

    def __init__(self, version: PypiVer, version_str: str,
                 prev_version: t.Optional[PypiVer],
                 ancestor_version: t.Optional[PypiVer],
                 core_versions: t.Dict[PypiVer, str],
                 versions_per_collection: t.Dict[str, t.Dict[PypiVer, str]],
                 core_collector: AnsibleCoreChangelogCollector,
                 ansible_changelog: ChangelogData,
                 collectors: t.List[CollectionChangelogCollector]):
        self.version = version
        self.version_str = version_str
        self.is_ancestor = False if ancestor_version is None else ancestor_version == version
        self.prev_version = prev_version = prev_version or ancestor_version
        self.core_versions = core_versions
        self.versions_per_collection = versions_per_collection
        self.core_collector = core_collector
        self.ansible_changelog = ansible_changelog
        self.collectors = collectors

        self.ansible_core_version = core_versions[version]
        self.prev_ansible_core_version = core_versions.get(prev_version) if prev_version else None

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
            added = False
            if prev_version:
                if not prev_collection_version:
                    self.added_collections.append((collector, collection_version))
                    added = True
                elif prev_collection_version == collection_version:
                    self.unchanged_collections.append((collector, collection_version))
                    continue

            self.changed_collections.append((
                collector, collection_version, prev_collection_version, added))


class CollectionMetadata:
    '''
    Stores metadata about one collection.
    '''

    changelog_url: t.Optional[str]

    def __init__(self, source: t.Optional[t.Mapping[str, t.Any]] = None):
        if source is None:
            source = {}
        self.changelog_url = source.get('changelog-url')


class CollectionsMetadata:
    '''
    Stores metadata about a set of collections.
    '''

    data: t.Dict[str, CollectionMetadata]

    def __init__(self, deps_dir: t.Optional[str]):
        self.data = {}
        if deps_dir is not None:
            collection_meta_path = os.path.join(deps_dir, 'collection-meta.yaml')
            if os.path.exists(collection_meta_path):
                data = load_yaml_file(collection_meta_path)
                if data and 'collections' in data:
                    for collection_name, collection_data in data['collections'].items():
                        self.data[collection_name] = CollectionMetadata(collection_data)

    def get_meta(self, collection_name: str) -> CollectionMetadata:
        result = self.data.get(collection_name)
        if result is None:
            result = CollectionMetadata()
            self.data[collection_name] = result
        return result


class Changelog:
    ansible_version: PypiVer
    ansible_ancestor_version: t.Optional[PypiVer]
    entries: t.List[ChangelogEntry]
    core_collector: AnsibleCoreChangelogCollector
    ansible_changelog: ChangelogData
    collection_collectors: t.List[CollectionChangelogCollector]
    collection_metadata: CollectionsMetadata

    def __init__(self,
                 ansible_version: PypiVer,
                 ansible_ancestor_version: t.Optional[PypiVer],
                 entries: t.List[ChangelogEntry],
                 core_collector: AnsibleCoreChangelogCollector,
                 ansible_changelog: ChangelogData,
                 collection_collectors: t.List[CollectionChangelogCollector],
                 collection_metadata: CollectionsMetadata):
        self.ansible_version = ansible_version
        self.ansible_ancestor_version = ansible_ancestor_version
        self.entries = entries
        self.core_collector = core_collector
        self.ansible_changelog = ansible_changelog
        self.collection_collectors = collection_collectors
        self.collection_metadata = collection_metadata


def get_changelog(
        ansible_version: PypiVer,
        deps_dir: t.Optional[str],
        deps_data: t.Optional[t.List[DependencyFileData]] = None,
        collection_cache: t.Optional[str] = None,
        ansible_changelog: t.Optional[ChangelogData] = None
        ) -> Changelog:
    dependencies: t.Dict[str, DependencyFileData] = {}

    ansible_changelog = ansible_changelog or ChangelogData.ansible(directory=deps_dir)
    ansible_ancestor_version_str = ansible_changelog.changes.ancestor
    ansible_ancestor_version = (
        PypiVer(ansible_ancestor_version_str) if ansible_ancestor_version_str else None
    )

    collection_metadata = CollectionsMetadata(deps_dir)

    if deps_dir is not None:
        for path in glob.glob(os.path.join(deps_dir, '*.deps'), recursive=False):
            deps_file = DepsFile(path)
            deps = deps_file.parse()
            deps.deps.pop('_python', None)
            version = PypiVer(deps.ansible_version)
            if version > ansible_version:
                print(f"Ignoring {path}, since {deps.ansible_version}"
                      f" is newer than {ansible_version}")
                continue
            dependencies[deps.ansible_version] = deps
    if deps_data:
        for deps in deps_data:
            dependencies[deps.ansible_version] = deps

    core_versions: t.Dict[PypiVer, str] = {}
    versions: t.Dict[str, t.Tuple[PypiVer, DependencyFileData]] = {}
    versions_per_collection: t.Dict[str, t.Dict[PypiVer, str]] = defaultdict(dict)
    for deps in dependencies.values():
        version = PypiVer(deps.ansible_version)
        versions[deps.ansible_version] = (version, deps)
        core_versions[version] = deps.ansible_core_version
        for collection_name, collection_version in deps.deps.items():
            versions_per_collection[collection_name][version] = collection_version

    core_collector = AnsibleCoreChangelogCollector(core_versions.values())
    collectors = [
        CollectionChangelogCollector(collection, versions_per_collection[collection].values())
        for collection in sorted(versions_per_collection.keys())
    ]
    asyncio_run(collect_changelogs(collectors, core_collector, collection_cache))

    changelog = []

    sorted_versions = collect_versions(versions, ansible_changelog.config)
    for index, (version_str, dummy) in enumerate(sorted_versions):
        version, deps = versions[version_str]
        prev_version = None
        if index + 1 < len(sorted_versions):
            prev_version = versions[sorted_versions[index + 1][0]][0]

        changelog.append(ChangelogEntry(
            version,
            version_str,
            prev_version,
            ansible_ancestor_version,
            core_versions,
            versions_per_collection,
            core_collector,
            ansible_changelog,
            collectors))

    return Changelog(
        ansible_version,
        ansible_ancestor_version,
        changelog,
        core_collector,
        ansible_changelog,
        collectors,
        collection_metadata)
