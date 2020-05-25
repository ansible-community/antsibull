# -*- coding: utf-8 -*-
# Author: Matt Clay <matt@mystile.com>
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Linting for changelog.yaml.
"""

import re

from typing import cast, Any, List, Optional, Tuple, Type

import semantic_version
import yaml

from .ansible import get_documentable_plugins
from .config import ChangelogConfig, CollectionDetails, PathsConfig
from .fragment import ChangelogFragment, ChangelogFragmentLinter


ISO_DATE_REGEX = re.compile('^[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])$')


class ChangelogYamlLinter:
    """
    Lint a changelogs/changelog.yaml file.
    """

    errors: List[Tuple[str, int, int, str]]
    path: str

    def __init__(self, path):
        self.errors = []
        self.path = path

    def check_version(self, version: Any, message: str) -> Optional[semantic_version.Version]:
        """
        Check that the given version is a valid semantic version.

        :arg version: Version string to check
        :arg message: Message to prepend to error
        :return: A ``semantic_version.Version`` object
        """
        try:
            if not isinstance(version, str):
                raise ValueError('Expecting string')
            return semantic_version.Version(version)
        except ValueError as exc:
            self.errors.append((self.path, 0, 0,
                                '{0}: error while parse version {1!r}: {2}'
                                .format(message, version, exc)))
            return None

    @staticmethod
    def _format_yaml_path(yaml_path: List[Any]) -> str:
        """
        Format path to YAML element as string.
        """
        return "{0}".format(" -> ".join([repr(component) for component in yaml_path]))

    def verify_type(self, value: Any, allowed_types: Tuple[Type[Any], ...],
                    yaml_path: List[Any], allow_none=False) -> bool:
        """
        Verify that a value is of a given type.

        :arg value: Value to check
        :arg allowed_types: Tuple with allowed types
        :arg yaml_path: Path to this object in the YAML file
        :arg allow_none: Whether ``None`` is an acceptable value
        """
        if allow_none and value is None:
            return True

        if isinstance(value, allowed_types):
            return True

        if len(allowed_types) == 1:
            allowed_types_str = '{0}'.format(str(allowed_types[0]))
        else:
            allowed_types_str = 'one of {0}'.format(
                ', '.join([str(allowed_type) for allowed_type in allowed_types]))
        if allow_none:
            allowed_types_str = 'null or {0}'.format(allowed_types_str)
        self.errors.append((self.path, 0, 0, '{0} is expected to be {1}, but got {2!r}'.format(
            self._format_yaml_path(yaml_path),
            allowed_types_str,
            value,
        )))
        return False

    def verify_plugin(self, plugin: dict, yaml_path: List[Any], is_module: bool) -> None:
        """
        Verify that a given dictionary is a plugin or module description.

        :arg plugin: The dictionary to check
        :arg yaml_path: Path to this dictionary in the YAML
        :arg is_module: Whether this is a module description or a plugin description
        """
        if self.verify_type(plugin, (dict, ), yaml_path):
            name = plugin.get('name')
            if self.verify_type(name, (str, ), yaml_path + ['name']):
                name = cast(str, name)
                if '.' in name:
                    self.errors.append((self.path, 0, 0, '{0} must not be a FQCN'.format(
                        self._format_yaml_path(yaml_path + ['name'])
                    )))
            self.verify_type(plugin.get('description'), (str, ), yaml_path + ['description'])
            namespace = plugin.get('namespace')
            if is_module:
                if self.verify_type(namespace, (str, ), yaml_path + ['namespace']):
                    namespace = cast(str, namespace)
                    if ' ' in namespace or '/' in namespace or '\\' in namespace:
                        self.errors.append((self.path, 0, 0, '{0} must not contain spaces or '
                                            'slashes'.format(
                                                self._format_yaml_path(yaml_path + ['namespace'])
                                            )))
            else:
                if namespace is not None:
                    self.errors.append((self.path, 0, 0, '{0} must be null'.format(
                        self._format_yaml_path(yaml_path + ['namespace'])
                    )))

    def lint_plugins(self, version_str: str, plugins_dict: dict):
        """
        Lint a plugin dictionary.

        :arg version_str: To which release the plugin dictionary belongs
        :arg plugins_dict: The plugin dictionary
        """
        for plugin_type, plugins in plugins_dict.items():
            if self.verify_type(plugin_type, (str, ), ['releases', version_str, 'plugins']):
                if plugin_type not in get_documentable_plugins() or plugin_type == 'module':
                    self.errors.append((
                        self.path, 0, 0,
                        'Unknown plugin type {0!r} in {1}'.format(
                            plugin_type, self._format_yaml_path(
                                ['releases', version_str, 'plugins']))))
            if self.verify_type(plugins, (list, ),
                                ['releases', version_str, 'plugins', plugin_type]):
                for idx, plugin in enumerate(plugins):
                    self.verify_plugin(plugin,
                                       ['releases', version_str, 'modules', plugin_type, idx],
                                       is_module=False)

    def lint_changes(self, fragment_linter: ChangelogFragmentLinter,
                     version_str: str, changes: dict):
        """
        Lint changes for an entry of the releases list.

        :arg fragment_linter: A fragment linter
        :arg version_str: The version the changes belongs to
        :arg entry: The changes dictionary
        """
        fragment = ChangelogFragment.from_dict(changes, self.path)
        for error in fragment_linter.lint(fragment):
            self.errors.append((error[0], error[1], error[2], '{1}: {0}'.format(
                error[3], self._format_yaml_path(['releases', version_str, 'changes']))))

    def lint_releases_entry(self, fragment_linter: ChangelogFragmentLinter,
                            version_str: str, entry: dict):
        """
        Lint an entry of the releases list.

        :arg fragment_linter: A fragment linter
        :arg version_str: The version this entry belongs to
        :arg entry: The releases list entry
        """
        release_date = entry.get('release_date')
        if self.verify_type(release_date, (str, ),
                            ['releases', version_str, 'release_date']):
            release_date = cast(str, release_date)
            if not ISO_DATE_REGEX.match(release_date):
                self.errors.append((self.path, 0, 0, '{0} must be a ISO date (YYYY-MM-DD)'.format(
                    self._format_yaml_path(['releases', version_str, 'release_date'])
                )))

        codename = entry.get('codename')
        self.verify_type(codename, (str, ),
                         ['releases', version_str, 'codename'], allow_none=True)

        changes = entry.get('changes')
        if self.verify_type(changes, (dict, ),
                            ['releases', version_str, 'changes'],
                            allow_none=True) and changes:
            self.lint_changes(fragment_linter, version_str, cast(dict, changes))

        modules = entry.get('modules')
        if self.verify_type(modules, (list, ),
                            ['releases', version_str, 'modules'],
                            allow_none=True) and modules:
            modules = cast(list, modules)
            for idx, plugin in enumerate(modules):
                self.verify_plugin(plugin,
                                   ['releases', version_str, 'modules', idx],
                                   is_module=True)

        plugins = entry.get('plugins')
        if self.verify_type(plugins, (dict, ),
                            ['releases', version_str, 'plugins'],
                            allow_none=True) and plugins:
            plugins = cast(dict, plugins)
            self.lint_plugins(version_str, plugins)

        fragments = entry.get('fragments')
        if self.verify_type(fragments, (list, ),
                            ['releases', version_str, 'fragments'],
                            allow_none=True) and fragments:
            fragments = cast(list, fragments)
            for idx, fragment in enumerate(fragments):
                self.verify_type(fragment, (str, ),
                                 ['releases', version_str, 'fragments', idx])

    def lint(self) -> List[Tuple[str, int, int, str]]:
        """
        Load and lint the changelog.yaml file.
        """
        try:
            with open(self.path, 'r') as changelog_fd:
                changelog_yaml = yaml.safe_load(changelog_fd)
        except Exception as exc:  # pylint: disable=broad-except
            self.errors.append((self.path, 0, 0, 'error while parsing YAML: {0}'.format(exc)))
            return self.errors

        ancestor_str = changelog_yaml.get('ancestor')
        if ancestor_str is not None:
            ancestor = self.check_version(ancestor_str, 'Invalid ancestor version')
        else:
            ancestor = None

        paths = PathsConfig.force_collection('')  # path doesn't matter
        config = ChangelogConfig.default(paths, CollectionDetails(paths))
        fragment_linter = ChangelogFragmentLinter(config)

        if self.verify_type(changelog_yaml.get('releases'), (dict, ), ['releases']):
            for version_str, entry in changelog_yaml['releases'].items():
                # Check version
                version = self.check_version(version_str, 'Invalid release version')
                if version is not None and ancestor is not None:
                    if version <= ancestor:
                        self.errors.append((self.path, 0, 0,
                                            'release version {0!r} must come after ancestor '
                                            'version {1!r}'.format(version_str, ancestor_str)))

                # Check release information
                if self.verify_type(entry, (dict, ), ['releases', version_str]):
                    self.lint_releases_entry(fragment_linter, version_str, entry)

        return self.errors


def lint_changelog_yaml(path: str) -> List[Tuple[str, int, int, str]]:
    """
    Lint a changelogs/changelog.yaml file.
    """
    return ChangelogYamlLinter(path).lint()
