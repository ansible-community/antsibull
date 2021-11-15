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
from .changelog import Changelog, ChangelogData, ChangelogEntry, CollectionsMetadata, get_changelog


#
# Changelog
#


PluginDataT = t.List[t.Tuple[str, str, ChangelogGenerator, t.Optional[ChangelogGeneratorEntry]]]


def _cleanup_plugins(entries: t.List[t.Any]) -> t.List[t.Any]:
    '''Remove duplicate module/plugin/object entries from the given list.
    '''
    result = []
    found_names = set()
    for entry in entries:
        name = entry['name']
        if name in found_names:
            continue
        result.append(entry)
        found_names.add(name)
    return result


def optimize_release_entry(entry: ChangelogGeneratorEntry) -> ChangelogGeneratorEntry:
    '''Remove duplicate entries from changelog entry.

    This can happen if entries from versions from different changelogs are combined
    which partially include each other's changes. This happens if for example the 1.1.0
    changelog continues the 1.0.2 changelog, and there was also a 1.0.3 release continuing
    the 1.0.2 changelog. The 1.0.3 changes are usually a subset of the 1.1.0 changes as
    they are backported bugfixes.
    '''
    entry.modules = _cleanup_plugins(entry.modules)
    for plugin_type, plugins in entry.plugins.items():
        entry.plugins[plugin_type] = _cleanup_plugins(plugins)
    for object_type, objects in entry.objects.items():
        entry.objects[object_type] = _cleanup_plugins(objects)
    for section, changes in entry.changes.items():
        if isinstance(changes, list):
            entry.changes[section] = sorted(set(changes))
    return entry


def _add_rst_table_row(builder: RstBuilder, column_widths: t.List[int], row: t.List[str]):
    lines = [[''] * len(column_widths)]
    for i, value in enumerate(row):
        for j, line in enumerate(value.splitlines()):
            if j >= len(lines):
                lines.append([''] * len(column_widths))
            lines[j][i] = line
    for line in lines:
        parts = ['|']
        for j, cell in enumerate(line):
            parts.append(' ' + cell + ' ' * (1 + column_widths[j] - len(cell)) + '|')
        builder.add_raw_rst(''.join(parts))


def _add_rst_table_line(builder: RstBuilder, column_widths: t.List[int], sep: str):
    parts = ['+']
    for w in column_widths:
        parts.append(sep * (w + 2) + '+')
    builder.add_raw_rst(''.join(parts))


def render_rst_table(builder: RstBuilder, headings: t.List[str],
                     cells: t.List[t.List[str]]) -> None:
    # Determine column widths
    column_widths = []
    for row in [headings] + cells:
        while len(row) > len(column_widths):
            column_widths.append(0)
        for i, value in enumerate(row):
            for line in value.splitlines():
                column_widths[i] = max(column_widths[i], len(line))

    # Add rows
    _add_rst_table_line(builder, column_widths, '-')
    _add_rst_table_row(builder, column_widths, headings)
    _add_rst_table_line(builder, column_widths, '=')
    for row in cells:
        _add_rst_table_row(builder, column_widths, row)
        _add_rst_table_line(builder, column_widths, '-')


def append_changelog_changes_collections(builder: RstBuilder,
                                         collection_metadata: CollectionsMetadata,
                                         changelog_entry: ChangelogEntry,
                                         is_last: bool) -> PluginDataT:
    result: PluginDataT = []

    if changelog_entry.changed_collections:
        builder.add_section('Included Collections' if is_last else 'Changed Collections', 1)
        builder.add_raw_rst(
            'If not mentioned explicitly, the changes are reported in the combined changelog'
            ' below.\n')
        headings = [
            'Collection',
            f'Ansible {changelog_entry.prev_version}',
            f'Ansible {changelog_entry.version_str}',
            'Notes'
        ]
        cells = []
        for (
                collector, collection_version, prev_collection_version
        ) in changelog_entry.changed_collections:
            row = [collector.collection, '', str(collection_version), '']
            if prev_collection_version is not None:
                row[1] = str(prev_collection_version)
            changelog = collector.changelog
            if changelog:
                release_entries = changelog.generator.collect(
                    squash=True,
                    after_version=prev_collection_version,
                    until_version=collection_version)
                if not release_entries:
                    row[-1] = "The collection did not have a changelog in this version."
                elif release_entries[0].empty:
                    row[-1] = "There are no changes recorded in the changelog."
                else:
                    result.append((
                        collector.collection,
                        f"{collector.collection}.",
                        changelog.generator,
                        optimize_release_entry(release_entries[0])))
            else:
                metadata = collection_metadata.get_meta(collector.collection)
                if metadata.changelog_url is not None:
                    row[-1] = (
                        "You can find the collection's changelog at"
                        f" `{metadata.changelog_url} <{metadata.changelog_url}>`_."
                    )
                else:
                    row[-1] = (
                        "Unfortunately, this collection does not provide changelog data in a"
                        " format that can be processed by the changelog generator."
                    )
            cells.append(row)
        render_rst_table(builder, headings, cells)
        builder.add_raw_rst('')

    return result


def append_changelog_changes_ansible(builder: RstBuilder,
                                     changelog_entry: ChangelogEntry) -> PluginDataT:
    changelog = changelog_entry.ansible_changelog

    release_entries = changelog.generator.collect(
        squash=True,
        after_version=str(changelog_entry.prev_version) if changelog_entry.prev_version else None,
        until_version=changelog_entry.version_str)

    if not release_entries:
        return []

    release_entry = optimize_release_entry(release_entries[0])

    release_summary = release_entry.changes.pop('release_summary', None)
    if release_summary:
        builder.add_section('Release Summary', 1)
        builder.add_raw_rst(t.cast(str, release_summary))
        builder.add_raw_rst('')

    if release_entry.empty:
        return []

    return [("", "", changelog.generator, release_entry)]


def append_changelog_changes_base(builder: RstBuilder,
                                  changelog_entry: ChangelogEntry) -> PluginDataT:
    base_name = 'Ansible-base'
    if (
            changelog_entry.base_collector.latest.major > 2 or
            changelog_entry.base_collector.latest.minor > 10
    ):
        base_name = 'Ansible-core'
    builder.add_section(base_name, 1)

    builder.add_raw_rst(f"Ansible {changelog_entry.version} contains {base_name} "
                        f"version {changelog_entry.ansible_base_version}.")
    if changelog_entry.prev_ansible_base_version:
        if changelog_entry.prev_ansible_base_version == changelog_entry.ansible_base_version:
            builder.add_raw_rst(f"This is the same version of {base_name} as in "
                                "the previous Ansible release.\n")
            return []

        builder.add_raw_rst(f"This is a newer version than version "
                            f"{changelog_entry.prev_ansible_base_version} contained in the "
                            f"previous Ansible release.\n")

    changelog = changelog_entry.base_collector.changelog
    if not changelog:
        return []

    release_entries = changelog.generator.collect(
        squash=True,
        after_version=changelog_entry.prev_ansible_base_version,
        until_version=changelog_entry.ansible_base_version)

    if not release_entries:
        builder.add_raw_rst(f"{base_name} did not have a changelog in this version.")
        return []

    release_entry = release_entries[0]

    if release_entry.empty:
        builder.add_raw_rst("There are no changes recorded in the changelog.")
        return []

    builder.add_raw_rst("The changes are reported in the combined changelog below.")
    return [(base_name, "ansible.builtin.", changelog.generator, release_entry)]


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


def dump_items(builder: RstBuilder, items: PluginDumpT) -> None:
    last_title = []
    for title, name, description in sorted(items):
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
    for name, prefix, dummy, release_entry in data:
        if release_entry:
            for plugin_type, plugin_datas in release_entry.plugins.items():
                for plugin_data in plugin_datas:
                    plugins.append((
                        # ['New Plugins', plugin_type.title(), name],
                        ['New Plugins', plugin_type.title()],
                        prefix + plugin_data['name'],
                        plugin_data['description']))
    dump_items(builder, plugins)


def add_objects(builder: RstBuilder, data: PluginDataT) -> None:
    objects: PluginDumpT = []
    for name, prefix, dummy, release_entry in data:
        if release_entry:
            for object_type, object_datas in release_entry.objects.items():
                for object_data in object_datas:
                    objects.append((
                        ['New {type}s'.format(type=object_type.title())],
                        prefix + object_data['name'],
                        object_data['description']))
    dump_items(builder, objects)


def add_modules(builder: RstBuilder, data: PluginDataT) -> None:
    modules: PluginDumpT = []
    for name, prefix, dummy, release_entry in data:
        if release_entry:
            for module in release_entry.modules:
                namespace = module.get('namespace') or ''
                if namespace.startswith('.ansible.collections.ansible_collections.'):
                    # Work around old antsibull-changelog versions which suffer from
                    # https://github.com/ansible-community/antsibull-changelog/issues/18
                    namespace = ''
                namespace = namespace.strip('.').split('.', 1) if namespace else []
                modules.append((
                    ['New Modules', name] + [ns.replace('_', ' ').title() for ns in namespace],
                    prefix + module['name'],
                    module['description']))
    dump_items(builder, modules)


def create_title_adder(builder: RstBuilder, title: str,
                       level: int) -> t.Generator[None, None, None]:
    builder.add_section(title, level)
    while True:
        yield


def append_removed_collections(builder: RstBuilder, changelog_entry: ChangelogEntry) -> None:
    if changelog_entry.removed_collections:
        builder.add_section('Removed Collections', 1)
        for collector, collection_version in changelog_entry.removed_collections:
            builder.add_list_item(f"{collector.collection} "
                                  f"(previously included version: {collection_version})")
        builder.add_raw_rst('')


def append_added_collections(builder: RstBuilder, changelog_entry: ChangelogEntry) -> None:
    if changelog_entry.added_collections:
        builder.add_section('Added Collections', 1)
        for collector, collection_version in changelog_entry.added_collections:
            builder.add_list_item(f"{collector.collection} (version {collection_version})")
        builder.add_raw_rst('')


def append_unchanged_collections(builder: RstBuilder, changelog_entry: ChangelogEntry) -> None:
    if changelog_entry.unchanged_collections:
        builder.add_section('Unchanged Collections', 1)
        for collector, collection_version in changelog_entry.unchanged_collections:
            builder.add_list_item(f"{collector.collection} (still version {collection_version})")
        builder.add_raw_rst('')


def append_changelog(builder: RstBuilder,
                     collection_metadata: CollectionsMetadata,
                     changelog_entry: ChangelogEntry,
                     is_last: bool) -> None:
    builder.add_section('v{0}'.format(changelog_entry.version_str), 0)

    builder.add_raw_rst('.. contents::')
    builder.add_raw_rst('  :local:')
    builder.add_raw_rst('  :depth: 2\n')

    # Add release summary for Ansible
    data = append_changelog_changes_ansible(builder, changelog_entry)

    append_removed_collections(builder, changelog_entry)
    append_added_collections(builder, changelog_entry)

    # Adds Ansible-base section
    data.extend(append_changelog_changes_base(builder, changelog_entry))
    builder.add_raw_rst('')

    # Adds list of changed collections
    data.extend(
        append_changelog_changes_collections(
            builder, collection_metadata, changelog_entry, is_last=is_last))

    # Adds all changes
    for section, section_title in DEFAULT_SECTIONS:
        maybe_add_section_title = create_title_adder(builder, section_title, 1)

        for name, dummy, dummy, release_entry in data:
            if not release_entry or release_entry.has_no_changes([section]):
                continue

            next(maybe_add_section_title)
            if name:
                builder.add_section(name, 2)
            release_entry.add_section_content(builder, section)
            builder.add_raw_rst('')

    # Adds new plugins and modules
    add_plugins(builder, data)
    add_modules(builder, data)
    add_objects(builder, data)

    # Adds list of unchanged collections
    append_unchanged_collections(builder, changelog_entry)


#
# Porting Guide
#


def append_porting_guide_section(builder: RstBuilder, changelog_entry: ChangelogEntry,
                                 maybe_add_title: t.Generator[None, None, None],
                                 section: str) -> None:
    maybe_add_section_title = create_title_adder(builder, section.replace('_', ' ').title(), 1)

    def check_changelog(
            name: str,
            changelog: t.Optional[ChangelogData],
            version: str,
            prev_version: t.Optional[str]) -> None:
        if not changelog:
            return
        entries = changelog.generator.collect(
            squash=True, after_version=prev_version, until_version=version)
        if not entries or entries[0].has_no_changes([section]):
            return
        next(maybe_add_title)
        next(maybe_add_section_title)
        if name:
            builder.add_section(name, 2)
        optimize_release_entry(entries[0]).add_section_content(builder, section)
        builder.add_raw_rst('')

    check_changelog(
        '',
        changelog_entry.ansible_changelog,
        changelog_entry.version_str,
        str(changelog_entry.prev_version) if changelog_entry.prev_version else None)
    is_core = (
        changelog_entry.base_collector.latest.major > 2 or
        changelog_entry.base_collector.latest.minor > 10
    )
    check_changelog(
        'Ansible-core' if is_core else 'Ansible-base',
        changelog_entry.base_collector.changelog,
        changelog_entry.ansible_base_version,
        changelog_entry.prev_ansible_base_version)
    for (
            collector, collection_version, prev_collection_version
    ) in changelog_entry.changed_collections:
        check_changelog(
            collector.collection,
            collector.changelog,
            collection_version,
            prev_collection_version)


def append_porting_guide(builder: RstBuilder, changelog_entry: ChangelogEntry) -> None:
    maybe_add_title = create_title_adder(
        builder, 'Porting Guide for v{0}'.format(changelog_entry.version_str), 0)

    for section in ['known_issues', 'breaking_changes', 'major_changes']:
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
        if changelog.ansible_version.major > 2:
            version = f"{changelog.ansible_version.major}"
        else:
            version = f"{changelog.ansible_version.major}.{changelog.ansible_version.minor}"
        builder.set_title(f"Ansible {version} Release Notes")

        if changelog.ansible_ancestor_version:
            builder.add_raw_rst(
                f"This changelog describes changes since"
                f" Ansible {changelog.ansible_ancestor_version}.\n"
            )

        builder.add_raw_rst('.. contents::\n  :local:\n  :depth: 2\n')

        entries = [entry for entry in changelog.entries if not entry.is_ancestor]
        for index, changelog_entry in enumerate(entries):
            append_changelog(
                builder,
                changelog.collection_metadata,
                changelog_entry,
                is_last=index + 1 == len(entries))

        return builder.generate().encode('utf-8')

    @staticmethod
    def _append_base_porting_guide_bytes(builder: RstBuilder, changelog: Changelog) -> None:
        base_porting_guide = changelog.base_collector.porting_guide
        if base_porting_guide:
            lines = base_porting_guide.decode('utf-8').splitlines()
            lines.append('')
            found_topics = False
            found_empty = False
            for line in lines:
                if not found_topics:
                    if line.startswith('.. contents::'):
                        found_topics = True
                    continue
                if not found_empty:
                    if line == '':
                        found_empty = True
                    continue
                builder.add_raw_rst(line)
            if not found_empty:
                print('WARNING: cannot find TOC of ansible-base porting guide!')

    @staticmethod
    def _get_porting_guide_bytes(changelog: Changelog) -> bytes:
        if changelog.ansible_version.major > 2:
            version = f"{changelog.ansible_version.major}"
            base_version = changelog.base_collector.latest
            base_version = f"{base_version.major}.{base_version.minor}"
        else:
            version = f"{changelog.ansible_version.major}.{changelog.ansible_version.minor}"
            base_version = f"{changelog.ansible_version.major}.{changelog.ansible_version.minor}"
        builder = RstBuilder()
        builder.add_raw_rst(
            f"..\n"
            f"   THIS DOCUMENT IS AUTOMATICALLY GENERATED BY ANTSIBULL! PLEASE DO NOT EDIT"
            f" MANUALLY! (YOU PROBABLY WANT TO EDIT porting_guide_base_{base_version}.rst)\n")
        builder.add_raw_rst(f".. _porting_{version}_guide:\n")
        builder.set_title(f"Ansible {version} Porting Guide")

        if changelog.ansible_version.major == 2:
            builder.add_raw_rst(
                # noqa: E501
                ".. warning::"
                "\n\n"
                "        "
                " In Ansible 2.10, many plugins and modules have migrated to"
                " Collections on `Ansible Galaxy <https://galaxy.ansible.com>`_. Your playbooks"
                " should continue to work without any changes. We recommend you start using the"
                " fully-qualified collection name (FQCN) in your playbooks as the explicit and"
                " authoritative indicator of which collection to use as some collections may"
                " contain duplicate module names."
                " You can search the `index of all modules"
                " <https://docs.ansible.com/ansible/2.10/collections/index_module.html>`_"
                " to find the collection a module has been relocated to."
                "\n\n"
                "This section discusses the behavioral changes between Ansible 2.9 and"
                " Ansible 2.10."
                "\n\n"
                "It is intended to assist in updating your playbooks, plugins and other parts of"
                " your Ansible infrastructure so they will work with this version of Ansible."
                "\n\n"
                "We suggest you read this page along with the `Ansible 2.10 Changelog <https://"
                "github.com/ansible-community/ansible-build-data/blob/main/2.10/"
                "CHANGELOG-v2.10.rst>`_"
                " to understand what updates you may need to make."
                "\n\n"
                "Since 2.10, Ansible consists of two parts:\n\n"
                "* ansible-base, which includes the command line tools with a small selection"
                " of plugins and modules, and\n"
                "* a `set of collections <https://github.com/ansible-community/ansible-build-data/"
                "blob/main/2.10/ansible.in>`_."
                "\n\n"
                "The :ref:`porting_2.10_guide_base` is included in this porting guide. The complete"
                " list of porting guides can be found at :ref:`porting guides <porting_guides>`."
                "\n"
            )

        builder.add_raw_rst('.. contents::\n  :local:\n  :depth: 2\n')

        # Determine ansible-base/-core version in previous major release
        prev_base_version = ''
        if any(entry.is_ancestor for entry in changelog.entries):
            # If there is an ancestor, the earliest ansible-base/-core version will be the
            # version used in the previous major release.
            prev_base_version = changelog.base_collector.earliest
            prev_base_version = f"{prev_base_version.major}.{prev_base_version.minor}"

        # Determine whether to include ansible-base/-core porting guide or not
        if changelog.ansible_version.major == 2 or base_version != prev_base_version:
            builder.add_raw_rst(
                # noqa: E501
                "\n"
                f"We suggest you read this page along with the `Ansible {version} Changelog"
                f" <https://github.com/ansible-community/ansible-build-data/blob/main/{version}/"
                f"CHANGELOG-v{version}.rst>`_ to understand what updates you may need to make."
                "\n")
            ReleaseNotes._append_base_porting_guide_bytes(builder, changelog)
        elif changelog.ansible_version.major == 3:
            # Special message for Ansible 3
            builder.add_raw_rst(
                # noqa: E501
                "\n"
                "Ansible 3 is based on Ansible-Base 2.10, which is the same major release as"
                " Ansible 2.10.  Therefore, there is no section on ansible-base in this porting"
                " guide.  If you are upgrading from Ansible 2.9, please first consult the"
                " Ansible 2.10 porting guide before continuing with the Ansible 3 porting guide."
                "\n\n"
                "We suggest you read this page along with the `Ansible 3 Changelog"
                " <https://github.com/ansible-community/ansible-build-data/blob/main/3/"
                "CHANGELOG-v3.rst>`_ to understand what updates you may need to make."
                "\n"
            )
        else:
            # Generic message if we again have two consecutive versions with the same ansible-core
            prev_version = changelog.ansible_version.major - 1
            prev_prev_version = changelog.ansible_version.major - 2
            builder.add_raw_rst(
                # noqa: E501
                "\n"
                f"Ansible {version} is based on Ansible-core {base_version}, which is the same"
                f" major release as Ansible {prev_version}.  Therefore, there is no section on"
                " ansible-core in this porting guide.  If you are upgrading from Ansible"
                f" {prev_prev_version}, please first consult the Ansible {prev_version} porting"
                f" guide before continuing with the Ansible {version} porting guide."
                "\n\n"
                f"We suggest you read this page along with the `Ansible {version} Changelog"
                f" <https://github.com/ansible-community/ansible-build-data/blob/main/{version}/"
                f"CHANGELOG-v{version}.rst>`_ to understand what updates you may need to make."
                "\n"
            )

        for porting_guide_entry in changelog.entries:
            if not porting_guide_entry.is_ancestor:
                append_porting_guide(builder, porting_guide_entry)

        return builder.generate().encode('utf-8')

    @classmethod
    def build(cls, changelog: Changelog) -> 'ReleaseNotes':
        if changelog.ansible_version.major > 2:
            version = f"{changelog.ansible_version.major}"
        else:
            version = f"{changelog.ansible_version.major}.{changelog.ansible_version.minor}"
        return cls(
            f"CHANGELOG-v{version}.rst",
            cls._get_changelog_bytes(changelog),
            f"porting_guide_{version}.rst",
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

    ansible_version: PypiVer = app_ctx.extra['ansible_version']
    data_dir: str = app_ctx.extra['data_dir']
    dest_data_dir: str = app_ctx.extra['dest_data_dir']
    collection_cache: t.Optional[str] = app_ctx.extra['collection_cache']

    changelog = get_changelog(ansible_version, deps_dir=data_dir, collection_cache=collection_cache)

    release_notes = ReleaseNotes.build(changelog)
    release_notes.write_changelog_to(dest_data_dir)
    release_notes.write_porting_guide_to(dest_data_dir)

    missing_changelogs = []
    last_entry = changelog.entries[0]
    last_version_collectors = [
        collector for collector in changelog.collection_collectors
        if last_entry.version in last_entry.versions_per_collection[collector.collection]
    ]
    for collector in last_version_collectors:
        if collector.changelog is None:
            missing_changelogs.append(collector.collection)
    if missing_changelogs:
        print(f"{len(missing_changelogs)} out of {len(last_version_collectors)} collections"
              f" have no compatible changelog:")
        for collection_name in missing_changelogs:
            meta = changelog.collection_metadata.get_meta(collection_name)
            entry = [collection_name]
            if meta.changelog_url:
                entry.append(f"(changelog URL: {meta.changelog_url})")
            print(f"    {'  '.join(entry)}")
    return 0
