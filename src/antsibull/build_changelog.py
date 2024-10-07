# Author: Felix Fontein <felix@fontein.de>
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020
"""Build Ansible changelog and porting guide."""

from __future__ import annotations

import asyncio
import os
import os.path
import typing as t
from dataclasses import dataclass

from antsibull_changelog.changelog_generator import (
    ChangelogEntry as ChangelogGeneratorEntry,
)
from antsibull_changelog.config import DEFAULT_SECTIONS, TextFormat
from antsibull_changelog.rendering.changelog import (
    add_section_content,
    create_document_renderer,
)
from antsibull_changelog.rendering.document import (
    AbstractRenderer,
    DocumentRenderer,
    SectionRenderer,
)
from antsibull_changelog.rendering.rst_document import RSTDocumentRenderer
from antsibull_core import app_context
from antsibull_core.logging import log
from antsibull_core.schemas.collection_meta import CollectionsMetadata
from packaging.version import Version as PypiVer

from .changelog import Changelog, ChangelogData, ChangelogEntry, get_changelog
from .utils.galaxy import create_galaxy_context

mlog = log.fields(mod=__name__)


class SectionAdder:
    parent: SectionAdder | AbstractRenderer
    section_name: str
    section: SectionRenderer | None

    def __init__(self, parent: SectionAdder | AbstractRenderer, section_name: str):
        self.parent = parent
        self.section_name = section_name
        self.section = None

    def get_section(self) -> SectionRenderer:
        if self.section is None:
            parent: AbstractRenderer
            if isinstance(self.parent, SectionAdder):
                parent = self.parent.get_section()
            else:
                parent = t.cast(AbstractRenderer, self.parent)
            self.section = parent.add_section(self.section_name)
        return self.section

    def close(self) -> None:
        if self.section is not None:
            self.section.close()


#
# Changelog
#

CHANGELOG_FORMATS = [TextFormat.RESTRUCTURED_TEXT, TextFormat.MARKDOWN]

PluginDataT = t.List[t.Tuple[str, str, t.Optional[ChangelogGeneratorEntry]]]


def _cleanup_plugins(entries: list[t.Any]) -> list[t.Any]:
    """Remove duplicate module/plugin/object entries from the given list."""
    result = []
    found_names = set()
    for entry in entries:
        name = entry["name"]
        if name in found_names:
            continue
        result.append(entry)
        found_names.add(name)
    return result


def optimize_release_entry(entry: ChangelogGeneratorEntry) -> ChangelogGeneratorEntry:
    """Remove duplicate entries from changelog entry.

    This can happen if entries from versions from different changelogs are combined
    which partially include each other's changes. This happens if for example the 1.1.0
    changelog continues the 1.0.2 changelog, and there was also a 1.0.3 release continuing
    the 1.0.2 changelog. The 1.0.3 changes are usually a subset of the 1.1.0 changes as
    they are backported bugfixes.
    """
    entry.modules = _cleanup_plugins(entry.modules)
    for plugin_type, plugins in entry.plugins.items():
        entry.plugins[plugin_type] = _cleanup_plugins(plugins)
    for object_type, objects in entry.objects.items():
        entry.objects[object_type] = _cleanup_plugins(objects)
    for section, changes in entry.changes.items():
        if isinstance(changes, list):
            entry.changes[section] = sorted(set(changes))
    return entry


def _add_table_row(
    lines: list[str], column_widths: list[int], row: list[str], sep: str
):
    row_lines = [[""] * len(column_widths)]
    for i, value in enumerate(row):
        for j, line in enumerate(value.splitlines()):
            if j >= len(row_lines):
                row_lines.append([""] * len(column_widths))
            row_lines[j][i] = line
    for cells in row_lines:
        parts = [sep]
        for j, cell in enumerate(cells):
            parts.append(" ")
            parts.append(cell)
            parts.append(" " * (1 + column_widths[j] - len(cell)))
            parts.append(sep)
        lines.append("".join(parts))


def _add_table_line(
    lines: list[str],
    column_widths: list[int],
    start_sep: str,
    mid_sep: str,
    end_sep: str,
    corner: str,
):
    parts = [corner]
    for w in column_widths:
        parts.append(start_sep)
        parts.append(mid_sep * w)
        parts.append(end_sep)
        parts.append(corner)
    lines.append("".join(parts))


def compute_column_widths(headings: list[str], cells: list[list[str]]) -> list[int]:
    column_widths: list[int] = []
    for row in [headings] + cells:
        while len(row) > len(column_widths):
            column_widths.append(0)
        for i, value in enumerate(row):
            for line in value.splitlines():
                column_widths[i] = max(column_widths[i], len(line))
    return column_widths


def render_rst_table(headings: list[str], cells: list[list[str]]) -> str:
    column_widths = compute_column_widths(headings, cells)
    lines: list[str] = []
    _add_table_line(lines, column_widths, "-", "-", "-", "+")
    _add_table_row(lines, column_widths, headings, "|")
    _add_table_line(lines, column_widths, "=", "=", "=", "+")
    for row in cells:
        _add_table_row(lines, column_widths, row, "|")
        _add_table_line(lines, column_widths, "-", "-", "-", "+")
    return "\n".join(lines)


def render_md_table(headings: list[str], cells: list[list[str]]) -> str:
    column_widths = compute_column_widths(headings, cells)
    lines: list[str] = []
    _add_table_row(lines, column_widths, headings, "|")
    _add_table_line(lines, column_widths, " ", "-", " ", "|")
    for row in cells:
        _add_table_row(lines, column_widths, row, "|")
    return "\n".join(lines)


def format_link(title: str, url: str, text_format: TextFormat) -> str:
    if text_format == TextFormat.RESTRUCTURED_TEXT:
        return f"`{title} <{url}>`_"
    if text_format == TextFormat.MARKDOWN:
        return f"`[{title}]({url})"
    raise ValueError(f"Unknown format {format}")


def render_table(
    renderer: AbstractRenderer,
    headings: list[str],
    cells: list[list[str]],
    text_format: TextFormat,
) -> None:
    table_renderers = {
        TextFormat.RESTRUCTURED_TEXT: render_rst_table,
        TextFormat.MARKDOWN: render_md_table,
    }
    table_renderer = table_renderers.get(text_format)
    if table_renderer is None:
        raise ValueError(f"Unknown format {text_format}")
    renderer.add_text(table_renderer(headings, cells), text_format=text_format)


def append_changelog_changes_collections(
    renderer: AbstractRenderer,
    collection_metadata: CollectionsMetadata,
    changelog_entry: ChangelogEntry,
    is_last: bool,
    text_format: TextFormat,
) -> PluginDataT:
    result: PluginDataT = []

    if changelog_entry.changed_collections:
        section = renderer.add_section(
            "Included Collections" if is_last else "Changed Collections"
        )
        section.add_text(
            "If not mentioned explicitly, the changes are reported in the combined changelog"
            " below.",
            text_format=TextFormat.RESTRUCTURED_TEXT,
        )
        section.ensure_paragraph_break()
        headings = [
            "Collection",
            f"Ansible {changelog_entry.prev_version}",
            f"Ansible {changelog_entry.version_str}",
            "Notes",
        ]
        cells = []
        for (
            collector,
            collection_version,
            prev_collection_version,
            newly_added,
        ) in changelog_entry.changed_collections:
            row = [collector.collection, "", str(collection_version), ""]
            if prev_collection_version is not None:
                row[1] = str(prev_collection_version)
            changelog = collector.changelog
            if newly_added:
                row[-1] = "The collection was added to Ansible"
            elif changelog:
                release_entries = changelog.generator.collect(
                    squash=True,
                    after_version=prev_collection_version,
                    until_version=collection_version,
                )
                if not release_entries:
                    row[-1] = "The collection did not have a changelog in this version."
                elif release_entries[0].empty:
                    row[-1] = "There are no changes recorded in the changelog."
                else:
                    result.append(
                        (
                            collector.collection,
                            f"{collector.collection}.",
                            optimize_release_entry(release_entries[0]),
                        )
                    )
            else:
                metadata = collection_metadata.get_meta(collector.collection)
                if metadata.changelog_url is not None:
                    link = format_link(
                        metadata.changelog_url,
                        metadata.changelog_url,
                        text_format=text_format,
                    )
                    row[-1] = f"You can find the collection's changelog at {link}."
                else:
                    row[-1] = (
                        "Unfortunately, this collection does not provide changelog data in a"
                        " format that can be processed by the changelog generator."
                    )
            cells.append(row)
        render_table(section, headings, cells, text_format)
        section.close()

    return result


def append_changelog_changes_ansible(
    renderer: AbstractRenderer, changelog_entry: ChangelogEntry
) -> PluginDataT:
    changelog = changelog_entry.ansible_changelog

    release_entries = changelog.generator.collect(
        squash=True,
        after_version=(
            str(changelog_entry.prev_version) if changelog_entry.prev_version else None
        ),
        until_version=changelog_entry.version_str,
    )

    if not release_entries:
        return []

    release_entry = optimize_release_entry(release_entries[0])

    release_summary = release_entry.changes.pop("release_summary", None)
    if release_summary:
        section = renderer.add_section("Release Summary")
        section.add_text(
            t.cast(str, release_summary), text_format=TextFormat.RESTRUCTURED_TEXT
        )
        section.close()

    if release_entry.empty:
        return []

    return [("", "", release_entry)]


def append_changelog_changes_core(
    renderer: AbstractRenderer, changelog_entry: ChangelogEntry
) -> PluginDataT:
    section = renderer.add_section("Ansible-core")
    try:
        section.add_text(
            f"Ansible {changelog_entry.version} contains ansible-core "
            f"version {changelog_entry.ansible_core_version}.",
            text_format=TextFormat.RESTRUCTURED_TEXT,
        )
        if changelog_entry.prev_ansible_core_version:
            if (
                changelog_entry.prev_ansible_core_version
                == changelog_entry.ansible_core_version
            ):
                section.add_text(
                    "This is the same version of ansible-core as in "
                    "the previous Ansible release.",
                    text_format=TextFormat.RESTRUCTURED_TEXT,
                )
                return []

            section.add_text(
                f"This is a newer version than version "
                f"{changelog_entry.prev_ansible_core_version} contained in the "
                f"previous Ansible release.",
                text_format=TextFormat.RESTRUCTURED_TEXT,
            )

        changelog = changelog_entry.core_collector.changelog
        if not changelog:
            return []

        section.ensure_paragraph_break()

        release_entries = changelog.generator.collect(
            squash=True,
            after_version=changelog_entry.prev_ansible_core_version,
            until_version=changelog_entry.ansible_core_version,
        )

        if not release_entries:
            section.add_text(
                "Ansible-core did not have a changelog in this version.",
                text_format=TextFormat.RESTRUCTURED_TEXT,
            )
            return []

        release_entry = release_entries[0]

        if release_entry.empty:
            section.add_text(
                "There are no changes recorded in the changelog.",
                text_format=TextFormat.RESTRUCTURED_TEXT,
            )
            return []

        section.add_text(
            "The changes are reported in the combined changelog below.",
            text_format=TextFormat.RESTRUCTURED_TEXT,
        )

        return [
            (
                "Ansible-core",
                "ansible.builtin.",
                release_entry,
            )
        ]
    finally:
        section.close()


def common_start(a: list[t.Any], b: list[t.Any]) -> int:
    """
    Given two sequences a and b, determines maximal index so that
    all elements up to that index are equal.
    """
    common_len = min(len(a), len(b))
    for i in range(common_len):
        if a[i] != b[i]:
            return i
    return common_len


PluginDumpT = t.List[t.Tuple[t.List[str], str, str]]


def _get_last_renderer(
    sections: list[SectionRenderer], renderer: AbstractRenderer
) -> AbstractRenderer:
    if sections:
        return sections[-1]
    return renderer


def dump_items(renderer: AbstractRenderer, items: PluginDumpT) -> None:
    last_title: list[str] = []
    sections: list[SectionRenderer] = []
    for title, name, description in sorted(items):
        if title != last_title:
            common = common_start(last_title, title)
            while len(sections) > common:
                sections.pop().close()
            while len(sections) < len(title):
                section = _get_last_renderer(sections, renderer).add_section(
                    title[len(sections)]
                )
                sections.append(section)
            last_title = title
        _get_last_renderer(sections, renderer).add_fragment(
            f"{name} - {description}", text_format=TextFormat.RESTRUCTURED_TEXT
        )

    while sections:
        sections.pop().close()


def add_plugins(renderer: AbstractRenderer, data: PluginDataT) -> None:
    plugins: PluginDumpT = []
    for _, prefix, release_entry in data:
        if release_entry:
            for plugin_type, plugin_datas in release_entry.plugins.items():
                for plugin_data in plugin_datas:
                    plugins.append(
                        (
                            # ['New Plugins', plugin_type.title(), name],
                            ["New Plugins", plugin_type.title()],
                            prefix + plugin_data["name"],
                            plugin_data["description"],
                        )
                    )
    dump_items(renderer, plugins)


def add_objects(renderer: AbstractRenderer, data: PluginDataT) -> None:
    objects: PluginDumpT = []
    for _, prefix, release_entry in data:
        if release_entry:
            for object_type, object_datas in release_entry.objects.items():
                for object_data in object_datas:
                    objects.append(
                        (
                            [f"New {object_type.title()}s"],
                            prefix + object_data["name"],
                            object_data["description"],
                        )
                    )
    dump_items(renderer, objects)


def add_modules(renderer: AbstractRenderer, data: PluginDataT) -> None:
    modules: PluginDumpT = []
    for name, prefix, release_entry in data:
        if release_entry:
            for module in release_entry.modules:
                namespace = module.get("namespace") or ""
                if namespace.startswith(".ansible.collections.ansible_collections."):
                    # Work around old antsibull-changelog versions which suffer from
                    # https://github.com/ansible-community/antsibull-changelog/issues/18
                    namespace = ""
                namespace = namespace.strip(".").split(".", 1) if namespace else []
                modules.append(
                    (
                        ["New Modules", name]
                        + [ns.replace("_", " ").title() for ns in namespace],
                        prefix + module["name"],
                        module["description"],
                    )
                )
    dump_items(renderer, modules)


def append_removed_collections(
    renderer: AbstractRenderer, changelog_entry: ChangelogEntry
) -> None:
    if changelog_entry.removed_collections:
        section = renderer.add_section("Removed Collections")
        for collector, collection_version in changelog_entry.removed_collections:
            section.add_fragment(
                f"{collector.collection} "
                f"(previously included version: {collection_version})",
                text_format=TextFormat.RESTRUCTURED_TEXT,
            )
        section.close()


def append_added_collections(
    renderer: AbstractRenderer, changelog_entry: ChangelogEntry
) -> None:
    if changelog_entry.added_collections:
        section = renderer.add_section("Added Collections")
        for collector, collection_version in changelog_entry.added_collections:
            section.add_fragment(
                f"{collector.collection} (version {collection_version})",
                text_format=TextFormat.RESTRUCTURED_TEXT,
            )
        section.close()


def append_unchanged_collections(
    renderer: AbstractRenderer, changelog_entry: ChangelogEntry
) -> None:
    if changelog_entry.unchanged_collections:
        section = renderer.add_section("Unchanged Collections")
        for collector, collection_version in changelog_entry.unchanged_collections:
            section.add_fragment(
                f"{collector.collection} (still version {collection_version})",
                text_format=TextFormat.RESTRUCTURED_TEXT,
            )
        section.close()


def append_changelog(
    renderer: AbstractRenderer,
    collection_metadata: CollectionsMetadata,
    changelog_entry: ChangelogEntry,
    is_last: bool,
    text_format: TextFormat,
) -> None:
    section = renderer.add_section(f"v{changelog_entry.version_str}")
    section.add_toc(max_depth=2)

    # Add release summary for Ansible
    data = append_changelog_changes_ansible(section, changelog_entry)

    append_removed_collections(section, changelog_entry)
    append_added_collections(section, changelog_entry)

    # Adds Ansible-core section
    data.extend(append_changelog_changes_core(section, changelog_entry))

    # Adds list of changed collections
    data.extend(
        append_changelog_changes_collections(
            section,
            collection_metadata,
            changelog_entry,
            is_last=is_last,
            text_format=text_format,
        )
    )

    # Adds all changes
    for section_name, section_title in DEFAULT_SECTIONS:
        section_renderer = SectionAdder(section, section_title)
        for name, _, release_entry in data:
            if not release_entry or release_entry.has_no_changes([section_name]):
                continue

            subsection_renderer = None
            if name:
                subsection_renderer = section_renderer.get_section().add_section(name)
            add_section_content(
                release_entry,
                subsection_renderer or section_renderer.get_section(),
                section_name,
            )
            if subsection_renderer:
                subsection_renderer.close()

        section_renderer.close()

    # Adds new plugins and modules
    add_plugins(section, data)
    add_modules(section, data)
    add_objects(section, data)

    # Adds list of unchanged collections
    append_unchanged_collections(section, changelog_entry)

    section.close()


def _compose_changelog(changelog: Changelog, text_format: TextFormat) -> str:
    flog = mlog.fields(func="_compose_changelog")

    renderer = create_document_renderer(text_format)
    version = f"{changelog.ansible_version.major}"
    renderer.set_title(f"Ansible {version} Release Notes")

    if changelog.ansible_ancestor_version:
        renderer.add_text(
            f"This changelog describes changes since"
            f" Ansible {changelog.ansible_ancestor_version}.",
            text_format=TextFormat.RESTRUCTURED_TEXT,
        )

    renderer.add_toc(max_depth=2)

    entries = [entry for entry in changelog.entries if not entry.is_ancestor]
    for index, changelog_entry in enumerate(entries):
        append_changelog(
            renderer,
            changelog.collection_metadata,
            changelog_entry,
            is_last=index + 1 == len(entries),
            text_format=text_format,
        )

    text = renderer.render()
    for warning in renderer.get_warnings():
        flog.warning(warning)
    return text


#
# Porting Guide
#


def append_porting_guide_section(
    changelog_entry: ChangelogEntry,
    maybe_add_title: SectionAdder,
    section: str,
) -> None:
    maybe_add_section_title = SectionAdder(
        maybe_add_title, section.replace("_", " ").title()
    )

    def check_changelog(
        name: str,
        changelog: ChangelogData | None,
        version: str,
        prev_version: str | None,
    ) -> None:
        if not changelog:
            return
        entries = changelog.generator.collect(
            squash=True, after_version=prev_version, until_version=version
        )
        if not entries or entries[0].has_no_changes([section]):
            return
        subsection = maybe_add_section_title.get_section()
        subsubsection = None
        if name:
            subsubsection = subsection.add_section(name)
        add_section_content(
            optimize_release_entry(entries[0]), subsubsection or subsection, section
        )
        if subsubsection:
            subsubsection.close()

    check_changelog(
        "",
        changelog_entry.ansible_changelog,
        changelog_entry.version_str,
        str(changelog_entry.prev_version) if changelog_entry.prev_version else None,
    )
    check_changelog(
        "Ansible-core",
        changelog_entry.core_collector.changelog,
        changelog_entry.ansible_core_version,
        changelog_entry.prev_ansible_core_version,
    )
    for (
        collector,
        collection_version,
        prev_collection_version,
        newly_added,
    ) in changelog_entry.changed_collections:
        if newly_added:
            continue
        check_changelog(
            collector.collection,
            collector.changelog,
            collection_version,
            prev_collection_version,
        )

    maybe_add_section_title.close()


def append_porting_guide(
    document: DocumentRenderer, changelog_entry: ChangelogEntry
) -> None:
    maybe_add_title = SectionAdder(
        document, f"Porting Guide for v{changelog_entry.version_str}"
    )

    if changelog_entry.added_collections:
        append_added_collections(maybe_add_title.get_section(), changelog_entry)

    for section_name in ["known_issues", "breaking_changes", "major_changes"]:
        append_porting_guide_section(changelog_entry, maybe_add_title, section_name)

    if changelog_entry.removed_collections:
        section = maybe_add_title.get_section().add_section("Removed Collections")
        for collector, collection_version in changelog_entry.removed_collections:
            section.add_fragment(
                f"{collector.collection} "
                f"(previously included version: {collection_version})",
                text_format=TextFormat.RESTRUCTURED_TEXT,
            )
        section.close()

    for section_name in ["removed_features", "deprecated_features"]:
        append_porting_guide_section(changelog_entry, maybe_add_title, section_name)

    maybe_add_title.close()


#
# Release Notes
#


@dataclass
class FileWithContent:
    filename: str
    content: bytes

    def write_to(self, dest_dir: str) -> None:
        path = os.path.join(dest_dir, self.filename)
        with open(path, "wb") as fd:
            fd.write(self.content)


class ReleaseNotes:
    changelogs: list[FileWithContent]
    porting_guide: FileWithContent

    def __init__(
        self,
        changelogs: list[FileWithContent],
        porting_guide: FileWithContent,
    ):
        self.changelogs = changelogs

        self.porting_guide = porting_guide

    @staticmethod
    def _get_changelog_bytes(changelog: Changelog, text_format: TextFormat) -> bytes:
        text = _compose_changelog(changelog, text_format)
        return text.encode("utf-8")

    @staticmethod
    def _append_core_porting_guide_bytes(
        renderer: AbstractRenderer, changelog: Changelog
    ) -> None:
        flog = mlog.fields(func="_append_core_porting_guide_bytes")
        core_porting_guide = changelog.core_collector.porting_guide
        if core_porting_guide:
            lines = core_porting_guide.decode("utf-8").splitlines()
            lines.append("")
            found_topics = False
            found_empty = False
            append_lines = []
            for line in lines:
                if not found_topics:
                    if line.startswith(".. contents::"):
                        found_topics = True
                    continue
                if not found_empty:
                    if line == "":
                        found_empty = True
                    continue
                append_lines.append(line)
            if not found_empty:
                flog.warning("Cannot find TOC of ansible-core porting guide!")
            if append_lines:
                renderer.add_text(
                    "\n".join(append_lines), text_format=TextFormat.RESTRUCTURED_TEXT
                )

    @staticmethod
    def _get_porting_guide_bytes(changelog: Changelog) -> bytes:
        flog = mlog.fields(func="ReleaseNotes._get_porting_guide_bytes")

        version = f"{changelog.ansible_version.major}"
        core_version_obj = changelog.core_collector.latest
        core_version = f"{core_version_obj.major}.{core_version_obj.minor}"

        document = RSTDocumentRenderer()
        document.set_raw_preamble(
            "..\n"
            f"   THIS DOCUMENT IS AUTOMATICALLY GENERATED BY ANTSIBULL! PLEASE DO NOT EDIT"
            f" MANUALLY! (YOU PROBABLY WANT TO EDIT porting_guide_core_{core_version}.rst)"
            "\n"
        )
        document.set_document_label(f"porting_{version}_guide")
        document.set_title(f"Ansible {version} Porting Guide")
        document.add_toc(max_depth=2)

        # Determine ansible-core version in previous major release
        prev_core_version = ""
        if any(entry.is_ancestor for entry in changelog.entries):
            # If there is an ancestor, the earliest ansible-core version will be the
            # version used in the previous major release.
            prev_core_version_obj = changelog.core_collector.earliest
            prev_core_version = (
                f"{prev_core_version_obj.major}.{prev_core_version_obj.minor}"
            )

        # Determine whether to include ansible-core porting guide or not
        if core_version != prev_core_version:
            document.add_text(
                # noqa: E501
                "\n" f"Ansible {version} is based on Ansible-core {core_version}." "\n",
                text_format=TextFormat.RESTRUCTURED_TEXT,
            )
            document.add_text(
                # noqa: E501
                "\n"
                f"We suggest you read this page along with the `Ansible {version} Changelog"
                f" <https://github.com/ansible-community/ansible-build-data/blob/main/{version}/"
                f"CHANGELOG-v{version}.md>`_ to understand what updates you may need to make."
                "\n",
                text_format=TextFormat.RESTRUCTURED_TEXT,
            )
            ReleaseNotes._append_core_porting_guide_bytes(document, changelog)
        else:
            # Generic message if we again have two consecutive versions with the same ansible-core
            prev_version = changelog.ansible_version.major - 1
            prev_prev_version = changelog.ansible_version.major - 2
            document.add_text(
                # noqa: E501
                "\n"
                f"Ansible {version} is based on Ansible-core {core_version}, which is the same"
                f" major release as Ansible {prev_version}.  Therefore, there is no section on"
                " ansible-core in this porting guide.  If you are upgrading from Ansible"
                f" {prev_prev_version}, please first consult the Ansible {prev_version} porting"
                f" guide before continuing with the Ansible {version} porting guide."
                "\n\n"
                f"We suggest you read this page along with the `Ansible {version} Changelog"
                f" <https://github.com/ansible-community/ansible-build-data/blob/main/{version}/"
                f"CHANGELOG-v{version}.md>`_ to understand what updates you may need to make."
                "\n",
                text_format=TextFormat.RESTRUCTURED_TEXT,
            )

        for porting_guide_entry in changelog.entries:
            if not porting_guide_entry.is_ancestor:
                append_porting_guide(document, porting_guide_entry)

        text = document.render()
        for warning in document.get_warnings():
            flog.warning(warning)

        return text.encode("utf-8")

    @classmethod
    def build(cls, changelog: Changelog) -> "ReleaseNotes":
        version = f"{changelog.ansible_version.major}"
        changelogs: list[FileWithContent] = []
        for text_format in CHANGELOG_FORMATS:
            changelogs.append(
                FileWithContent(
                    f"CHANGELOG-v{version}.{text_format.to_extension()}",
                    cls._get_changelog_bytes(changelog, text_format),
                )
            )
        return cls(
            changelogs,
            FileWithContent(
                f"porting_guide_{version}.rst", cls._get_porting_guide_bytes(changelog)
            ),
        )

    def write_changelog_to(self, dest_dir: str) -> None:
        for changelog in self.changelogs:
            changelog.write_to(dest_dir)

    def write_porting_guide_to(self, dest_dir: str) -> None:
        self.porting_guide.write_to(dest_dir)


def build_changelog() -> int:
    """Create changelog and porting guide CLI command."""
    app_ctx = app_context.app_ctx.get()
    lib_ctx = app_context.lib_ctx.get()

    ansible_version: PypiVer = app_ctx.extra["ansible_version"]
    data_dir: str = app_ctx.extra["data_dir"]
    dest_data_dir: str = app_ctx.extra["dest_data_dir"]
    collection_cache: str | None = lib_ctx.collection_cache

    galaxy_context = asyncio.run(create_galaxy_context())
    changelog = get_changelog(
        ansible_version,
        galaxy_context=galaxy_context,
        deps_dir=data_dir,
        collection_cache=collection_cache,
    )

    release_notes = ReleaseNotes.build(changelog)
    release_notes.write_changelog_to(dest_data_dir)
    release_notes.write_porting_guide_to(dest_data_dir)

    missing_changelogs = []
    last_entry = changelog.entries[0]
    last_version_collectors = [
        collector
        for collector in changelog.collection_collectors
        if last_entry.version
        in last_entry.versions_per_collection[collector.collection]
    ]
    for collector in last_version_collectors:
        if collector.changelog is None:
            missing_changelogs.append(collector.collection)
    if missing_changelogs:
        print(
            f"{len(missing_changelogs)} out of {len(last_version_collectors)} collections"
            f" have no compatible changelog:"
        )
        for collection_name in missing_changelogs:
            meta = changelog.collection_metadata.get_meta(collection_name)
            entry = [collection_name]
            if meta.changelog_url:
                entry.append(f"(changelog URL: {meta.changelog_url})")
            print(f"    {'  '.join(entry)}")
    return 0
