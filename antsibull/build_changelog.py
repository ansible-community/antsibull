# coding: utf-8
# Author: Felix Fontein <tkuratom@redhat.com>
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

import os
import os.path
import typing as t

from packaging.version import Version as PypiVer

from antsibull_changelog.changelog_generator import (
    ChangelogGenerator,
    ChangelogEntry as ChangelogGeneratorEntry,
)
from antsibull_changelog.config import DEFAULT_SECTIONS
from antsibull_changelog.rst import RstBuilder

from . import app_context
from .changelog import (
    Changelog,
    ChangelogEntry,
    CollectionChangelogCollector,
    AnsibleBaseChangelogCollector,
    get_changelog,
)


#
# Variant 1: Top-level are Ansible Base and collections;
#            below are changelogs of these collections.
#


def append_ansible_base_changelog(builder: RstBuilder, changelog_entry: ChangelogEntry) -> None:
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

    generator = changelog_entry.base_collector.changelog_generator
    if not same_version and generator:
        builder.add_raw_rst('.. contents::')
        builder.add_raw_rst('  :local:')
        builder.add_raw_rst('  :depth: 1\n')

        generator.generate_to(
            builder, 1, squash=True,
            after_version=changelog_entry.prev_ansible_base_version,
            until_version=changelog_entry.ansible_base_version)


def append_collection_changelog(builder: RstBuilder, changelog_entry: ChangelogEntry,
                                collector: CollectionChangelogCollector,
                                collection_version: str,
                                prev_collection_version: t.Optional[str]) -> None:
    if collector in changelog_entry.added_collections:
        builder.add_section(f"{collector.collection} (New)", 1)
        builder.add_raw_rst(f"The collection {collector.collection} was "
                            f"added in Ansible {changelog_entry.version}.\n")
    else:
        builder.add_section(collector.collection, 1)
        builder.add_raw_rst(f"Ansible {changelog_entry.version} contains "
                            f"{collector.collection} version {collection_version}.")
        if changelog_entry.prev_version:
            builder.add_raw_rst(f"This is a newer version than version "
                                f"{prev_collection_version} contained in the "
                                f"previous Ansible release.\n")
        else:
            builder.add_raw_rst('')

    changelog = collector.changelog
    generator = collector.changelog_generator
    if not changelog or not generator:
        builder.add_raw_rst(f"Unfortunately, {collector.collection} has no Ansible "
                            f"compatible changelog.\n")
        # TODO: add link to collection's changelog
        return

    release_entries = generator.collect(
        squash=True, after_version=prev_collection_version, until_version=collection_version)

    if not release_entries:
        builder.add_raw_rst("The collection did not have a changelog in this version.\n")
        return
    if release_entries[0].empty:
        builder.add_raw_rst("There are no changes recorded in the changelog.\n")
        return

    builder.add_raw_rst('.. contents::')
    builder.add_raw_rst('  :local:')
    builder.add_raw_rst('  :depth: 1\n')

    for release in release_entries:
        generator.append_changelog_entry(
            builder, release, start_level=1, add_version=False)


def append_changelog_entries_1(builder: RstBuilder, changelog_entry: ChangelogEntry) -> None:
    '''
    Top-level are Ansible Base and collections; below are changelogs of these collections.
    '''
    if changelog_entry.base_collector.changelog:
        append_ansible_base_changelog(builder, changelog_entry)

    for (
            collector, collection_version, prev_collection_version
    ) in changelog_entry.changed_collections:
        append_collection_changelog(builder, changelog_entry, collector,
                                    collection_version, prev_collection_version)


#
# Variant 2: Top-level are collections with no changelog,
#            and the sections of a single changelog entry.
#


PluginDataT = t.List[t.Tuple[str, str, ChangelogGenerator, t.List[ChangelogGeneratorEntry]]]


def append_changelog_changes_collections(builder: RstBuilder,
                                         changelog_entry: ChangelogEntry) -> PluginDataT:
    result: PluginDataT = []

    if changelog_entry.changed_collections:
        builder.add_section('Changed Collections', 1)
        for (
                collector, collection_version, prev_collection_version
        ) in changelog_entry.changed_collections:
            if prev_collection_version is None:
                msg = f"{collector.collection} was upgraded to version {collection_version}."
            else:
                msg = f"{collector.collection} was upgraded from version {prev_collection_version}"
                msg += f" to version {collection_version}."
            msg += "\n"
            generator = collector.changelog_generator
            if generator:
                release_entries = generator.collect(
                    squash=True,
                    after_version=prev_collection_version,
                    until_version=collection_version)
                if not release_entries:
                    msg += "The collection did not have a changelog in this version."
                elif release_entries[0].empty:
                    msg += "There are no changes recorded in the changelog."
                else:
                    result.append((
                        collector.collection,
                        f"{collector.collection}.",
                        generator,
                        release_entries))
                    msg += "The changes are reported in the combined changelog below."
            else:
                msg += "Unfortunately, this collection does not provide changelog data in a format "
                msg += "that can be processed by the changelog generator."
                # TODO: add link to collection's changelog

            builder.add_list_item(msg)
        builder.add_raw_rst('')

    return result


def append_changelog_changes_base(builder: RstBuilder,
                                  changelog_entry: ChangelogEntry) -> PluginDataT:
    builder.add_section('Ansible Base', 1)

    builder.add_raw_rst(f"Ansible {changelog_entry.version} contains Ansible-base "
                        f"version {changelog_entry.ansible_base_version}.")
    if changelog_entry.prev_ansible_base_version:
        if changelog_entry.prev_ansible_base_version == changelog_entry.ansible_base_version:
            builder.add_raw_rst("This is the same version of Ansible-base as in "
                                "the previous Ansible release.\n")
            return []

        builder.add_raw_rst(f"This is a newer version than version "
                            f"{changelog_entry.prev_ansible_base_version} contained in the "
                            f"previous Ansible release.\n")

    generator = changelog_entry.base_collector.changelog_generator
    if not generator:
        return []

    release_entries = generator.collect(
        squash=True,
        after_version=changelog_entry.prev_ansible_base_version,
        until_version=changelog_entry.ansible_base_version)

    if not release_entries:
        builder.add_raw_rst("Ansible-base did not have a changelog in this version.")
        return []

    if release_entries[0].empty:
        builder.add_raw_rst("There are no changes recorded in the changelog.")
        return []

    builder.add_raw_rst("The changes are reported in the combined changelog below.")
    return [("Ansible Base", "ansible.builtin.", generator, release_entries)]


def common_start(a: t.List[t.Any], b: t.List[t.Any]) -> int:
    '''
    Given two sequences a and b, determines maximal index so that
    all elements up to that index are equal.
    '''
    common_len = min(len(a), len(b))
    for i in range(common_len):
        if a[i] != b[i]:
            return i
    return common_len


PluginDumpT = t.List[t.Tuple[t.List[str], str, str]]


def dump_plugins(builder: RstBuilder, plugins: PluginDumpT) -> None:
    last_title = []
    for title, name, description in sorted(plugins):
        if title != last_title:
            if last_title:
                builder.add_raw_rst('')
            for i in range(common_start(last_title, title), len(title)):
                builder.add_section(title[i], i + 1)
            last_title = title
        builder.add_list_item(f"{name} - {description}")

    if last_title:
        builder.add_raw_rst('')


def add_plugins(builder: RstBuilder, data: PluginDataT) -> None:
    plugins: PluginDumpT = []
    for name, prefix, _, release_entries in data:
        for release_entry in release_entries:
            for plugin_type, plugin_datas in release_entry.plugins.items():
                for plugin_data in plugin_datas:
                    plugins.append((
                        # ['New Plugins', plugin_type.title(), name],
                        ['New Plugins', plugin_type.title()],
                        prefix + plugin_data['name'],
                        plugin_data['description']))
    dump_plugins(builder, plugins)


def add_modules(builder: RstBuilder, data: PluginDataT) -> None:
    modules: PluginDumpT = []
    for name, prefix, _, release_entries in data:
        for release_entry in release_entries:
            for module in release_entry.modules:
                namespace = module['namespace'].split('.', 1) if module['namespace'] else []
                modules.append((
                    ['New Modules', name] + [ns.replace('_', ' ').title() for ns in namespace],
                    prefix + module['name'],
                    module['description']))
    dump_plugins(builder, modules)


def create_title_adder(builder: RstBuilder, title: str,
                       level: int) -> t.Generator[None, None, None]:
    builder.add_section(title, level)
    while True:
        yield


def append_changelog_entries_2(builder: RstBuilder, changelog_entry: ChangelogEntry) -> None:
    '''
    Top-level are collections with no changelog, and the sections of a single changelog entry.
    '''
    data = append_changelog_changes_base(builder, changelog_entry)
    builder.add_raw_rst('')
    data.extend(append_changelog_changes_collections(builder, changelog_entry))

    for section, section_title in DEFAULT_SECTIONS:
        maybe_add_section_title = create_title_adder(builder, section_title, 1)

        for name, _, _, release_entries in data:
            if not release_entries or release_entries[0].has_no_changes([section]):
                continue

            next(maybe_add_section_title)
            builder.add_section(name, 2)
            release_entries[0].add_section_content(builder, section)
            builder.add_raw_rst('')

    add_plugins(builder, data)
    add_modules(builder, data)


#
# Generic Changelog Code
#


def append_changelog(builder: RstBuilder, changelog_entry: ChangelogEntry) -> None:
    builder.add_section('v{0}'.format(changelog_entry.version_str), 0)

    builder.add_raw_rst('.. contents::')
    builder.add_raw_rst('  :local:')
    builder.add_raw_rst('  :depth: 2\n')

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

    # append_changelog_entries_1(builder, changelog_entry)
    append_changelog_entries_2(builder, changelog_entry)


#
# Porting Guide
#


def append_porting_guide_section(builder: RstBuilder, changelog_entry: ChangelogEntry,
                                 maybe_add_title: t.Generator[None, None, None],
                                 section: str) -> None:
    maybe_add_section_title = create_title_adder(builder, section.replace('_', ' ').title(), 1)

    def check_changelog(
            name: str,
            collector: t.Union[AnsibleBaseChangelogCollector, CollectionChangelogCollector],
            version: str,
            prev_version: t.Optional[str]) -> None:
        generator = collector.changelog_generator
        if not generator:
            return
        entries = generator.collect(
            squash=True, after_version=prev_version, until_version=version)
        if not entries or entries[0].has_no_changes([section]):
            return
        next(maybe_add_title)
        next(maybe_add_section_title)
        builder.add_section(name, 2)
        entries[0].add_section_content(builder, section)
        builder.add_raw_rst('')

    check_changelog(
        'Ansible Base',
        changelog_entry.base_collector,
        changelog_entry.ansible_base_version,
        changelog_entry.prev_ansible_base_version)
    for (
            collector, collection_version, prev_collection_version
    ) in changelog_entry.changed_collections:
        check_changelog(
            collector.collection, collector, collection_version, prev_collection_version)


def append_porting_guide(builder: RstBuilder, changelog_entry: ChangelogEntry) -> None:
    maybe_add_title = create_title_adder(
        builder, 'Porting Guide for v{0}'.format(changelog_entry.version_str), 0)

    for section in ['breaking_changes', 'major_changes']:
        append_porting_guide_section(builder, changelog_entry, maybe_add_title, section)

    if changelog_entry.removed_collections:
        next(maybe_add_title)
        builder.add_section('Removed Collections', 1)
        for collector, collection_version in changelog_entry.removed_collections:
            builder.add_list_item(f"{collector.collection} "
                                  f"(previously included version: {collection_version})")
        builder.add_raw_rst('')

    for section in ['removed_features', 'deprecated_features']:
        append_porting_guide_section(builder, changelog_entry, maybe_add_title, section)


def insert_after_heading(lines: t.List[str], content: str) -> None:
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


#
# Release Notes
#


class ReleaseNotes:
    changelog_filename: str
    changelog_bytes: bytes

    porting_guide_filename: str
    porting_guide_bytes: bytes

    def __init__(self, changelog_filename: str, changelog_bytes: bytes,
                 porting_guide_filename: str, porting_guide_bytes: bytes):
        self.changelog_filename = changelog_filename
        self.changelog_bytes = changelog_bytes

        self.porting_guide_filename = porting_guide_filename
        self.porting_guide_bytes = porting_guide_bytes

    @staticmethod
    def _get_changelog_bytes(changelog: Changelog) -> bytes:
        builder = RstBuilder()
        builder.set_title(
            f"Ansible {changelog.acd_version.major}.{changelog.acd_version.minor} Release Notes")
        builder.add_raw_rst('.. contents::\n  :local:\n  :depth: 2\n')

        for changelog_entry in changelog.entries:
            append_changelog(builder, changelog_entry)

        return builder.generate().encode('utf-8')

    @staticmethod
    def _get_porting_guide_bytes(changelog: Changelog) -> bytes:
        builder = RstBuilder()
        base_porting_guide = changelog.base_collector.porting_guide
        if base_porting_guide:
            lines = base_porting_guide.decode('utf-8').splitlines()
            lines.append('')
            # insert_after_heading(lines, '\n.. contents::\n  :local:\n  :depth: 2')
            for line in lines:
                builder.add_raw_rst(line)
        else:
            builder.add_raw_rst(
                f".. _porting_{changelog.acd_version.major}."
                f"{changelog.acd_version.minor}_guide:\n")
            builder.set_title(
                f"Ansible {changelog.acd_version.major}.{changelog.acd_version.minor}"
                f" Porting Guide")
            builder.add_raw_rst('.. contents::\n  :local:\n  :depth: 2\n')

        for porting_guide_entry in changelog.entries:
            append_porting_guide(builder, porting_guide_entry)

        return builder.generate().encode('utf-8')

    @classmethod
    def build(cls, changelog: Changelog) -> 'ReleaseNotes':
        return cls(
            f"CHANGELOG-v{changelog.acd_version.major}.{changelog.acd_version.minor}.rst",
            cls._get_changelog_bytes(changelog),
            f"porting_guide_{changelog.acd_version.major}.{changelog.acd_version.minor}.rst",
            cls._get_porting_guide_bytes(changelog),
        )

    def write_changelog_to(self, dest_dir: str) -> None:
        path = os.path.join(dest_dir, self.changelog_filename)
        with open(path, 'wb') as changelog_fd:
            changelog_fd.write(self.changelog_bytes)

    def write_porting_guide_to(self, dest_dir: str) -> None:
        path = os.path.join(dest_dir, self.porting_guide_filename)
        with open(path, 'wb') as porting_guide_fd:
            porting_guide_fd.write(self.porting_guide_bytes)


def build_changelog() -> int:
    '''Create changelog and porting guide CLI command.'''
    app_ctx = app_context.app_ctx.get()

    acd_version: PypiVer = app_ctx.extra['acd_version']
    deps_dir: str = app_ctx.extra['deps_dir']
    dest_dir: str = app_ctx.extra['dest_dir']
    collection_cache: t.Optional[str] = app_ctx.extra['collection_cache']

    changelog = get_changelog(acd_version, deps_dir=deps_dir, collection_cache=collection_cache)

    release_notes = ReleaseNotes.build(changelog)
    release_notes.write_changelog_to(dest_dir)
    release_notes.write_porting_guide_to(dest_dir)

    missing_changelogs = []
    for collector in changelog.collection_collectors:
        if collector.changelog is None:
            missing_changelogs.append(collector.collection)
    if missing_changelogs:
        print(f"{len(missing_changelogs)} out of {len(changelog.collection_collectors)} collections"
              f" have no compatible changelog:")
        for changelog in missing_changelogs:
            print(f"    {changelog}")
    return 0
