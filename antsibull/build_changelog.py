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
    return f"docs/docsite/rst/porting_guides/porting_guide_{version}.rst"


def read_porting_guide_file(tarball_path: str, version: PypiVer) -> t.Optional[bytes]:
    filename = get_porting_guide_filename(version)
    return read_file(tarball_path, lambda fn: fn == filename)


class CollectionChangelogCollector:
    collection: str
    versions: t.List[SemVer]
    earliest: SemVer
    latest: SemVer

    changelog: t.Optional[ChangesData]

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
    porting_guide: t.Optional[bytes]

    def __init__(self, versions: t.ValuesView[str]):
        self.versions = sorted(PypiVer(version) for version in versions)
        self.earliest = self.versions[0]
        self.latest = self.versions[-1]

        paths = PathsConfig.force_ansible('')
        collection_details = CollectionDetails(paths)
        self.config = ChangelogConfig.default(paths, collection_details)

        self.changelog_data = None
        self.changelog = None
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
                    print(path, os.path.join(path, pg_path), root)
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

        self.changelog = ChangesData.concatenate(changelogs)

    async def download_github(self, aio_session: 'aiohttp.client.ClientSession'):
        branch_url = (f"https://raw.githubusercontent.com/ansible/ansible/"
                      f"stable-{self.latest.major}.{self.latest.minor}/")

        # Changelog
        query_url = f"{branch_url}/changelogs/changelog.yaml"
        async with aio_session.get(query_url) as response:
            changelog = await response.read()
        changelog_data = yaml.load(changelog, Loader=yaml.SafeLoader)
        self.changelog = ChangesData(self.config, '/', changelog_data)

        # Porting Guide
        query_url = f"{branch_url}/{get_porting_guide_filename(self.latest)}"
        async with aio_session.get(query_url) as response:
            self.porting_guide = await response.read()


async def collect_changelogs(collectors: t.List[CollectionChangelogCollector],
                             base_collector: AnsibleBaseChangelogCollector,
                             collection_cache: t.Optional[str]):
    with tempfile.TemporaryDirectory() as tmp_dir:
        async with aiohttp.ClientSession() as aio_session:
            async with asyncio_pool.AioPool(size=THREAD_MAX) as pool:
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
                 collectors: t.List[CollectionChangelogCollector]):
        self.version = version
        self.version_str = version_str
        self.prev_version = prev_version
        self.base_versions = base_versions
        self.versions_per_collection = versions_per_collection
        self.base_collector = base_collector
        self.collectors = collectors

        self.ansible_base_version = base_versions[version]
        self.prev_ansible_base_version = base_versions.get(prev_version) if prev_version else None

        self.removed_collections = []
        self.added_collections = []
        self.unchanged_collections = []
        self.changed_collections = []
        for collector in collectors:
            if version not in versions_per_collection[collector.collection]:
                print(f"WARNING: {collector.collection} is not included in Ansible {version}")

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


def append_ansible_base_changelog(builder: RstBuilder, changelog_entry: ChangelogEntry):
    builder.add_section('Ansible Base', 1)

    builder.add_raw_rst(f"Ansible {changelog_entry.version} contains Ansible-base "
                        f"version {changelog_entry.ansible_base_version}.")
    same_version = False
    if changelog_entry.prev_ansible_base_version:
        if changelog_entry.prev_ansible_base_version == changelog_entry.ansible_base_version:
            builder.add_raw_rst("This is the same version of Ansible-base as in "
                                "the previous Ansible release.\n")
            same_version = True
        else:
            builder.add_raw_rst(f"This is a newer version than version "
                                f"{changelog_entry.prev_ansible_base_version} contained in the "
                                f"previous Ansible release.\n")

    if not same_version:
        builder.add_raw_rst('.. contents::')
        builder.add_raw_rst('  :local:')
        builder.add_raw_rst('  :depth: 5\n')

        generator = ChangelogGenerator(
            changelog_entry.base_collector.config, changelog_entry.base_collector.changelog,
            plugins=None, fragments=None, flatmap=True)
        generator.generate_to(
            builder, 1, squash=True,
            after_version=changelog_entry.prev_ansible_base_version,
            until_version=changelog_entry.ansible_base_version)


def append_collection_changelog(builder: RstBuilder, changelog_entry: ChangelogEntry,
                                collector: CollectionChangelogCollector,
                                collection_version: str, prev_collection_version: t.Optional[str]):
    if collector in changelog_entry.added_collections:
        builder.add_section(f"{collector.collection.title()} (New)", 1)
        builder.add_raw_rst(f"The collection {collector.collection} was "
                            f"added in Ansible {changelog_entry.version}.\n")
    else:
        builder.add_section(collector.collection.title(), 1)
        builder.add_raw_rst(f"Ansible {changelog_entry.version} contains "
                            f"{collector.collection} version {collection_version}.")
        if changelog_entry.prev_version:
            builder.add_raw_rst(f"This is a newer version than version "
                                f"{prev_collection_version} contained in the "
                                f"previous Ansible release.\n")
        else:
            builder.add_raw_rst('')

    changelog = collector.changelog
    if not changelog:
        builder.add_raw_rst(f"Unfortunately, {collector.collection} has no Ansible "
                            f"compatible changelog.\n")
        # TODO: add link to collection's changelog
        return

    # TODO: actually check that there are no release information for this version range!
    if not changelog.releases:
        builder.add_raw_rst("There are no changes recorded in the changelog, or "
                            "the collection did not have a changelog in this version.\n")
        return

    flatmap = True  # TODO
    generator = ChangelogGenerator(
        collector.config, changelog,
        plugins=None, fragments=None, flatmap=flatmap)

    builder.add_raw_rst('.. contents::')
    builder.add_raw_rst('  :local:')
    builder.add_raw_rst('  :depth: 5\n')

    generator.generate_to(
        builder, 1, squash=True,
        after_version=prev_collection_version,
        until_version=collection_version)


def append_changelog(builder: RstBuilder, changelog_entry: ChangelogEntry):
    builder.add_section('v{0}'.format(changelog_entry.version_str), 0)

    if changelog_entry.removed_collections:
        builder.add_section('Removed Collections', 1)
        for collector, collection_version in changelog_entry.removed_collections:
            builder.add_list_item(f"{collector.collection} "
                                  f"(previously included version: {collection_version})")
        builder.add_raw_rst('')
    if changelog_entry.added_collections:
        builder.add_section('Added Collections', 1)
        for collector, collection_version in changelog_entry.added_collections:
            builder.add_list_item(f"{collector.collection} (version {collection_version})")
        builder.add_raw_rst('')
    if changelog_entry.unchanged_collections:
        builder.add_section('Unchanged Collections', 1)
        for collector, collection_version in changelog_entry.unchanged_collections:
            builder.add_list_item(f"{collector.collection} (still version {collection_version})")
        builder.add_raw_rst('')

    if changelog_entry.base_collector.changelog:
        append_ansible_base_changelog(builder, changelog_entry)

    for (
            collector, collection_version, prev_collection_version
    ) in changelog_entry.changed_collections:
        append_collection_changelog(builder, changelog_entry, collector,
                                    collection_version, prev_collection_version)


def append_porting_guide(builder: RstBuilder, changelog_entry: ChangelogEntry):
    def add_title():
        yield
        builder.add_section('v{0}'.format(changelog_entry.version_str), 0)
        while True:
            yield

    maybe_add_title = add_title()

    if changelog_entry.removed_collections:
        next(maybe_add_title)
        builder.add_section('Removed Collections', 1)
        for collector, collection_version in changelog_entry.removed_collections:
            builder.add_list_item(f"{collector.collection} "
                                  f"(previously included version: {collection_version})")
        builder.add_raw_rst('')

    if changelog_entry.base_collector.changelog:
        next(maybe_add_title)
        append_ansible_base_changelog(builder, changelog_entry)

    for (
            collector, collection_version, prev_collection_version
    ) in changelog_entry.changed_collections:
        next(maybe_add_title)
        append_collection_changelog(builder, changelog_entry, collector,
                                    collection_version, prev_collection_version)


def write_changelog(path: str, acd_version: PypiVer, changelog: t.List[ChangelogEntry]):
    builder = RstBuilder()
    builder.set_title(f"Ansible {acd_version.major}.{acd_version.minor} Release Notes")
    builder.add_raw_rst('.. contents::\n  :local:\n  :depth: 2\n')

    for changelog_entry in changelog:
        append_changelog(builder, changelog_entry)

    with open(path, 'wb') as changelog_fd:
        changelog_fd.write(builder.generate().encode('utf-8'))


def insert_after_heading(lines: t.List[str], content: str):
    has_heading = False
    for index, line in enumerate(lines):
        if line.startswith('***') and line == '*' * len(line):
            has_heading = True
        elif has_heading:
            if line:
                has_heading = False
            else:
                # First empty line after top-level heading: insert TOC
                lines.insert(index, content)
                return


def write_porting_guide(path: str, acd_version: PypiVer,
                        porting_guide: t.List[ChangelogEntry],
                        base_collector: AnsibleBaseChangelogCollector):
    builder = RstBuilder()
    base_porting_guide = base_collector.porting_guide
    if base_porting_guide:
        lines = base_porting_guide.decode('utf-8').splitlines()
        # insert_after_heading(lines, '\n.. contents::\n  :local:\n  :depth: 2')
        for line in lines:
            builder.add_raw_rst(line)
    else:
        builder.add_raw_rst(f".. _porting_{acd_version.major}.{acd_version.minor}_guide:\n")
        builder.set_title(f"Ansible {acd_version.major}.{acd_version.minor} Porting Guide")
        builder.add_raw_rst('.. contents::\n  :local:\n  :depth: 2\n')

    for porting_guide_entry in porting_guide:
        append_porting_guide(builder, porting_guide_entry)

    with open(path, 'wb') as porting_guide_fd:
        porting_guide_fd.write(builder.generate().encode('utf-8'))


def get_changelog_data(
        acd_version: PypiVer, deps_dir: str, collection_cache: str
        ) -> t.Tuple[t.List[ChangelogEntry], AnsibleBaseChangelogCollector]:
    base_versions: t.Dict[PypiVer, str] = dict()
    versions: t.List[t.Tuple[str, PypiVer, DependencyFileData]] = []
    versions_per_collection: t.Dict[str, t.Dict[PypiVer, str]] = defaultdict(dict)
    for path in glob.glob(os.path.join(deps_dir, '*.deps'), recursive=False):
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
    asyncio.run(collect_changelogs(collectors, base_collector, collection_cache))

    changelog = []

    for index, (version_str, version, deps) in enumerate(reversed(versions)):
        if index + 1 < len(versions):
            prev_version = versions[len(versions) - index - 2][1]
        else:
            prev_version = None

        changelog.append(ChangelogEntry(
            version, version_str, prev_version,
            base_versions, versions_per_collection,
            base_collector, collectors))

    return changelog, base_collector


def build_changelog(args):
    acd_version = args.acd_version
    changelog, base_collector = get_changelog_data(
        acd_version, args.deps_dir, args.collection_cache)

    changelog_filename = f"CHANGELOG-v{acd_version.major}.{acd_version.minor}.rst"
    write_changelog(
        os.path.join(args.dest_dir, changelog_filename),
        acd_version, changelog)

    porting_guide_filename = f"porting_guide_v{acd_version.major}.{acd_version.minor}.rst"
    write_porting_guide(
        os.path.join(args.dest_dir, porting_guide_filename),
        acd_version, changelog, base_collector)
