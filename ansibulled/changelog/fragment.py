# -*- coding: utf-8 -*-
# Author: Matt Clay <matt@mystile.com>
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020


import abc
import os

import docutils.utils
import rstcheck
import yaml

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping


def load_fragments(paths, config, fragment_paths=None, exceptions=None):
    """
    :type path: PathsConfig
    :type config: ChangelogConfig
    :type fragment_paths: list[str] | None
    :type exceptions: list[tuple[str, Exception]] | None
    """
    if not fragment_paths:
        fragments_dir = os.path.join(paths.changelog_dir, config.notes_dir)
        fragment_paths = [
            os.path.join(fragments_dir, path)
            for path in os.listdir(fragments_dir) if not path.startswith('.')]

    fragments = []

    for path in fragment_paths:
        try:
            fragments.append(ChangelogFragment.load(path))
        except Exception as ex:
            if exceptions is not None:
                exceptions.append((path, ex))
            else:
                raise

    return fragments


class ChangelogFragment:
    """Changelog fragment loader."""
    def __init__(self, content, path):
        """
        :type content: dict[str, list[str]]
        :type path: str
        """
        self.content = content
        self.path = path
        self.name = os.path.basename(path)

    def remove(self):
        """Remove changelog fragment from disk."""
        try:
            os.remove(self.path)
        except Exception:
            pass

    @staticmethod
    def load(path):
        """Load a ChangelogFragment from a file.
        :type path: str
        """
        with open(path, 'r') as fragment_fd:
            content = yaml.safe_load(fragment_fd)

        return ChangelogFragment(content, path)

    @staticmethod
    def from_dict(data, path=''):
        """Create a ChangelogFragment from a dictionary.
        :type data: dict
        """
        return ChangelogFragment(data, path)

    @staticmethod
    def combine(fragments):
        """Combine fragments into a new fragment.
        :type fragments: list[ChangelogFragment]
        :rtype: dict[str, list[str] | str]
        """
        result = {}

        for fragment in fragments:
            for section, content in fragment.content.items():
                if isinstance(content, list):
                    if section not in result:
                        result[section] = []

                    result[section] += content
                else:
                    result[section] = content

        return result


class ChangelogFragmentLinter:
    """Linter for ChangelogFragments."""
    def __init__(self, config):
        """
        :type config: ChangelogConfig
        """
        self.config = config

    def _lint_section(self, errors, fragment, section, lines):
        """
        :type errors: list[(str, int, int, str)]
        :type fragment: ChangelogFragment
        :type section: str
        """
        if section == self.config.prelude_name:
            if not isinstance(lines, str):
                errors.append((fragment.path, 0, 0,
                               'section "%s" must be type str '
                               'not %s' % (section, type(lines).__name__)))
        else:
            # doesn't account for prelude but only the RM should be adding those
            if not isinstance(lines, list):
                errors.append((fragment.path, 0, 0,
                               'section "%s" must be type list '
                               'not %s' % (section, type(lines).__name__)))

            if section not in self.config.sections:
                errors.append((fragment.path, 0, 0, 'invalid section: %s' % section))

    def _lint_lines(self, errors, fragment, section, lines):
        """
        :type errors: list[(str, int, int, str)]
        :type fragment: ChangelogFragment
        :type section: str
        """
        if isinstance(lines, list):
            for line in lines:
                if not isinstance(line, str):
                    errors.append((fragment.path, 0, 0,
                                   'section "%s" list items must be type str '
                                   'not %s' % (section, type(line).__name__)))
                    continue

                results = rstcheck.check(
                    line, filename=fragment.path,
                    report_level=docutils.utils.Reporter.WARNING_LEVEL)
                errors += [(fragment.path, 0, 0, result[1]) for result in results]
        elif isinstance(lines, str):
            results = rstcheck.check(
                lines, filename=fragment.path,
                report_level=docutils.utils.Reporter.WARNING_LEVEL)
            errors += [(fragment.path, 0, 0, result[1]) for result in results]

    def lint(self, fragment):
        """Lint a ChangelogFragment.
        :type fragment: ChangelogFragment
        :rtype: list[(str, int, int, str)]
        """
        errors = []

        if isinstance(fragment.content, Mapping):
            for section, lines in fragment.content.items():
                self._lint_section(errors, fragment, section, lines)
                self._lint_lines(errors, fragment, section, lines)

        else:
            errors.append((fragment.path, 0, 0,
                           'file must be a mapping not %s' % (type(fragment.content).__name__, )))

        return errors


class FragmentResolver(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def resolve(self, release):
        """Return a list of ChangelogFragment objects from the given fragment names
        :type release: dict
        :rtype: list[ChangelogFragment]
        """


class SimpleFragmentResolver(FragmentResolver):
    def __init__(self, fragments):
        """
        :type fragments: list[ChangelogFragment]
        """
        self.fragments = dict()
        for fragment in fragments:
            self.fragments[fragment.name] = fragment

    def resolve(self, release):
        """Return a list of ChangelogFragment objects from the given fragment names
        :type release: dict
        :rtype: list[ChangelogFragment]
        """
        return [self.fragments[fragment] for fragment in release.get('fragments', [])]
