# -*- coding: utf-8 -*-
# Author: Matt Clay <matt@mystile.com>
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Generate reStructuredText changelog from ChangesBase instance.
"""

import collections
import os

import packaging.version
import semantic_version

from .rst import RstBuilder
from .utils import LOGGER, is_release_version


def generate_changelog(paths, config, changes, plugins=None, fragments=None, flatmap=True):
    """Generate the changelog.
    :type paths: PathsConfig
    :type config: ChangelogConfig
    :type changes: ChangesBase
    :type plugins: list[PluginDescription] | None
    :type fragments: list[ChangelogFragment] | None
    :type flatmap: bool
    """
    if plugins is not None or fragments is not None:
        if plugins is not None:
            changes.prune_plugins(plugins)
        if fragments is not None and config.changes_format == 'classic':
            changes.prune_fragments(fragments)
        changes.save()

    major_minor_version = '.'.join(
        changes.latest_version.split('.')[:config.changelog_filename_version_depth])
    changelog_path = os.path.join(
        paths.changelog_dir, config.changelog_filename_template % major_minor_version)

    generator = ChangelogGenerator(config, changes, plugins, fragments, flatmap)
    rst = generator.generate()

    with open(changelog_path, 'wb') as changelog_fd:
        changelog_fd.write(rst.encode('utf-8'))


class ChangelogGenerator:
    """Changelog generator."""
    def __init__(self, config, changes, plugins=None, fragments=None, flatmap=True):
        """
        :type config: ChangelogConfig
        :type changes: ChangesBase
        :type plugins: list[PluginDescription] | None
        :type fragments: list[ChangelogFragment] | None
        :type flatmap: bool
        """
        self.config = config
        self.changes = changes
        self.plugins = {}
        self.modules = []
        self.flatmap = flatmap

        self.plugin_resolver = changes.get_plugin_resolver(plugins)
        self.fragment_resolver = changes.get_fragment_resolver(fragments)

    def _collect_versions(self, after_version=None, until_version=None):
        Version = (semantic_version.Version if self.config.is_collection
                   else packaging.version.Version)

        result = []
        for version in sorted(self.changes.releases, reverse=True, key=Version):
            if after_version is not None:
                if Version(version) <= Version(after_version):
                    continue
            if until_version is not None:
                if Version(version) > Version(until_version):
                    continue
            result.append(version)
        return result

    @staticmethod
    def _get_entry_config(release_entries, entry_version):
        if entry_version not in release_entries:
            release_entries[entry_version] = dict(
                modules=[],
                plugins={},
            )
            release_entries[entry_version]['changes'] = dict()

        return release_entries[entry_version]

    @staticmethod
    def _update_modules_plugins(entry_config, release):
        entry_config['modules'] += release.get('modules', [])

        for plugin_type, plugins in release.get('plugins', {}).items():
            if plugin_type not in entry_config['plugins']:
                entry_config['plugins'][plugin_type] = []

            entry_config['plugins'][plugin_type] += plugins

    def _collect(self, squash=False, after_version=None, until_version=None):
        release_entries = collections.OrderedDict()
        entry_version = until_version or self.changes.latest_version
        entry_fragment = None

        for version in self._collect_versions(
                after_version=after_version, until_version=until_version):
            release = self.changes.releases[version]

            if not squash:
                if is_release_version(self.config, version):
                    # next version is a release, it needs its own entry
                    entry_version = version
                    entry_fragment = None
                elif not is_release_version(self.config, entry_version):
                    # current version is a pre-release, next version needs its own entry
                    entry_version = version
                    entry_fragment = None

            entry_config = self._get_entry_config(release_entries, entry_version)

            dest_changes = entry_config['changes']

            for fragment in self.fragment_resolver.resolve(release):
                for section, lines in fragment.content.items():
                    if section == self.config.prelude_name:
                        if entry_fragment:
                            LOGGER.info('skipping prelude in version %s due to newer '
                                        'prelude in version %s',
                                        version, entry_version)
                            continue

                        # lines is a str in this case!
                        entry_fragment = lines
                        dest_changes[section] = lines
                    elif section in dest_changes:
                        dest_changes[section].extend(lines)
                    else:
                        dest_changes[section] = list(lines)

            self._update_modules_plugins(entry_config, release)

        return release_entries

    def generate_to(self, builder, start_level=0, squash=False,
                    after_version=None, until_version=None):
        """Generate the changelog.
        :type builder: RstBuilder
        :type start_level: int
        """
        release_entries = self._collect(
            squash=squash, after_version=after_version, until_version=until_version)

        for version, release in release_entries.items():
            if not squash:
                builder.add_section('v%s' % version, start_level)

            combined_fragments = release['changes']

            for section_name in self.config.sections:
                self._add_section(builder, combined_fragments, section_name,
                                  start_level=start_level)

            self._add_plugins(builder, release['plugins'], start_level=start_level)
            self._add_modules(builder, release['modules'], flatmap=self.flatmap,
                              start_level=start_level)

    def generate(self):
        """Generate the changelog.
        :rtype: str
        """
        latest_version = self.changes.latest_version
        codename = self.changes.releases[latest_version].get('codename')
        major_minor_version = '.'.join(
            latest_version.split('.')[:self.config.changelog_filename_version_depth])

        builder = RstBuilder()
        title = self.config.title or 'Ansible'
        if codename:
            builder.set_title('%s %s "%s" Release Notes' % (title, major_minor_version, codename))
        else:
            builder.set_title('%s %s Release Notes' % (title, major_minor_version))
        builder.add_raw_rst('.. contents:: Topics\n')

        if self.changes.ancestor and self.config.mention_ancestor:
            builder.add_raw_rst(
                'This changelog describes changes after version {0}.\n'
                .format(self.changes.ancestor))
        else:
            builder.add_raw_rst('')

        self.generate_to(builder, 0)

        return builder.generate()

    def _add_section(self, builder, combined_fragments, section_name, start_level=0):
        if section_name not in combined_fragments:
            return

        section_title = self.config.sections[section_name]

        builder.add_section(section_title, start_level + 1)

        content = combined_fragments[section_name]

        if isinstance(content, list):
            for rst in sorted(content):
                builder.add_raw_rst('- %s' % rst)
        else:
            builder.add_raw_rst(content)

        builder.add_raw_rst('')

    def _add_plugins(self, builder, plugin_types_and_names, start_level=0):
        if not plugin_types_and_names:
            return

        have_section = False

        for plugin_type in sorted(plugin_types_and_names):
            plugin_names = plugin_types_and_names.get(plugin_type, [])
            if self.config.changes_format != 'classic':
                plugin_names = [plugin['name'] for plugin in plugin_names]
            plugins = self.plugin_resolver.resolve(plugin_type, plugin_names)

            if not plugins:
                continue

            if not have_section:
                have_section = True
                builder.add_section('New Plugins', start_level + 1)

            builder.add_section(plugin_type.title(), start_level + 2)

            for plugin in sorted(plugins, key=lambda plugin: plugin['name']):
                builder.add_raw_rst('- %s - %s' % (plugin['name'], plugin['description']))

            builder.add_raw_rst('')

    def _add_modules(self, builder, module_names, flatmap, start_level=0):
        if not module_names:
            return

        if self.config.changes_format != 'classic':
            module_names = [module['name'] for module in module_names]

        modules = dict(
            (module['name'], module)
            for module in self.plugin_resolver.resolve('module', module_names))
        previous_section = None

        modules_by_namespace = collections.defaultdict(list)

        for module_name in sorted(modules):
            module = modules[module_name]

            modules_by_namespace[module['namespace']].append(module)

        for namespace in sorted(modules_by_namespace):
            parts = namespace.split('.')

            section = parts.pop(0).replace('_', ' ').title()

            if not previous_section:
                builder.add_section('New Modules', start_level + 1)

            if section != previous_section and section:
                builder.add_section(section, start_level + 2)

            previous_section = section

            subsection = '.'.join(parts)

            if subsection:
                builder.add_section(subsection, start_level + 3)

            for module in modules_by_namespace[namespace]:
                module_name = module['name']
                if not flatmap and namespace:
                    module_name = '%s.%s' % (namespace, module_name)

                builder.add_raw_rst('- %s - %s' % (module_name, module['description']))

            builder.add_raw_rst('')
