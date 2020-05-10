# -*- coding: utf-8 -*-
# Author: Matt Clay <matt@mystile.com>
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Linting for changelog.yaml.
"""

from collections.abc import Mapping

import semantic_version
import yaml

from .ansible import get_documentable_plugins
from .config import ChangelogConfig
from .fragment import ChangelogFragment, ChangelogFragmentLinter


def check_version(errors, version, message, path):
    try:
        return semantic_version.Version(version)
    except Exception as e:
        errors.append((path, 0, 0,
                       '{0}: error while parse version "{1}": {2}'.format(message, version, e)))


def format_yaml_path(yaml_path):
    return "'{0}'".format("' -> '".join(yaml_path))


def verify_type(errors, value, allowed_types, yaml_path, path, allow_none=False):
    if allow_none and value is None:
        return True

    if not isinstance(allowed_types, tuple):
        allowed_types = (allowed_types, )

    if isinstance(value, allowed_types):
        return True

    if len(allowed_types) == 1:
        allowed_types_str = '{0}'.format(str(allowed_types[0]))
    else:
        allowed_types_str = 'one of {0}'.format(
            ', '.join([str(allowed_type) for allowed_type in allowed_types]))
    if allow_none:
        allowed_types_str = 'null or {0}'.format(allowed_types_str)
    errors.append((path, 0, 0, '{0} is expected to be {1}, but got {2!r}'.format(
        format_yaml_path(yaml_path),
        allowed_types_str,
        value,
    )))
    return False


def verify_plugin(errors, plugin, yaml_path, path, is_module):
    if verify_type(errors, plugin, Mapping, yaml_path, path):
        name = plugin.get('name')
        if verify_type(errors, name, str, yaml_path + ['name'], path):
            if '.' in name:
                errors.append((path, 0, 0, '{0} must not be a FQCN'.format(
                    format_yaml_path(yaml_path + ['name'])
                )))
        verify_type(errors, plugin.get('description'), str, yaml_path + ['description'], path)
        namespace = plugin.get('namespace')
        if is_module:
            if verify_type(errors, namespace, str, yaml_path + ['namespace'],
                           path, allow_none=True):
                if ' ' in namespace or '/' in namespace or '\\' in namespace:
                    errors.append((path, 0, 0, '{0} must not contain spaces or slashes'.format(
                        format_yaml_path(yaml_path + ['namespace'])
                    )))
        else:
            if namespace is not None:
                errors.append((path, 0, 0, '{0} must be null'.format(
                    format_yaml_path(yaml_path + ['namespace'])
                )))


def lint_plugins(errors, path, version_str, plugins):
    for k, v in plugins.items():
        if verify_type(errors, k, str,
                       ['releases', version_str, 'plugins'], path=path):
            if k not in get_documentable_plugins() or k == 'module':
                errors.append((path, 0, 0,
                               'Unknown plugin type "{0}" in {1}'.format(
                                k, format_yaml_path(['releases', version_str, 'plugins']))))
        if verify_type(errors, v, list,
                       ['releases', version_str, 'plugins', k], path=path):
            for i, plugin in enumerate(v):
                verify_plugin(errors, plugin,
                              ['releases', version_str, 'modules', k, i],
                              path=path, is_module=False)


def lint_releases_entry(errors, path, fragment_linter, version_str, entry):
    codename = entry.get('codename')
    verify_type(errors, codename, str,
                ['releases', version_str, 'codename'], path=path, allow_none=True)

    changes = entry.get('changes')
    if verify_type(errors, changes, Mapping,
                   ['releases', version_str, 'changes'],
                   path=path, allow_none=True) and changes:
        if changes is not None:
            fragment = ChangelogFragment.from_dict(changes, path)
            errors += fragment_linter.lint(fragment)

    modules = entry.get('modules')
    if verify_type(errors, modules, list,
                   ['releases', version_str, 'modules'],
                   path=path, allow_none=True) and modules:
        for i, plugin in enumerate(modules):
            verify_plugin(errors, plugin,
                          ['releases', version_str, 'modules', i],
                          path=path, is_module=True)

    plugins = entry.get('plugins')
    if verify_type(errors, plugins, dict,
                   ['releases', version_str, 'plugins'],
                   path=path, allow_none=True) and plugins:
        lint_plugins(errors, path, version_str, plugins)

    fragments = entry.get('fragments')
    if verify_type(errors, fragments, list,
                   ['releases', version_str, 'fragments'],
                   path=path, allow_none=True) and fragments:
        for i, fragment in enumerate(fragments):
            verify_type(errors, fragment, str,
                        ['releases', version_str, 'fragments', i], path=path)


def lint_changelog_yaml(path):
    errors = []

    try:
        with open(path, 'r') as changelog_fd:
            changelog_yaml = yaml.safe_load(changelog_fd)
    except Exception as e:
        errors.append((path, 0, 0, 'error while parsing YAML: {0}'.format(e)))
        return errors

    ancestor_str = changelog_yaml.get('ancestor')
    if ancestor_str is not None:
        ancestor = check_version(errors, ancestor_str, 'Invalid ancestor version', path=path)
    else:
        ancestor = None

    config = ChangelogConfig.default()
    fragment_linter = ChangelogFragmentLinter(config)

    if verify_type(errors, changelog_yaml.get('releases'), Mapping, ['releases'], path=path):
        for version_str, entry in changelog_yaml['releases'].items():
            # Check version
            version = check_version(errors, version_str, 'Invalid release version', path=path)
            if version is not None and ancestor is not None:
                if version <= ancestor:
                    errors.append((path, 0, 0,
                                   'release version "{0}" must come after ancestor '
                                   'version "{1}"'.format(version_str, ancestor_str)))

            # Check release information
            if verify_type(errors, entry, Mapping, ['releases', version_str], path=path):
                lint_releases_entry(errors, path, fragment_linter, version_str, entry)

    return errors
