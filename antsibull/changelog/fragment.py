# -*- coding: utf-8 -*-
# Author: Matt Clay <matt@mystile.com>
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Changelog fragment loading, modification and linting.
"""

import os

from typing import Any, Dict, List, Optional, Union, Tuple

import docutils.utils
import rstcheck
import yaml

from .config import PathsConfig, ChangelogConfig


class ChangelogFragment:
    """
    A changelog fragment.
    """

    content: Dict[str, Union[List[str], str]]
    path: str
    name: str

    def __init__(self, content: Dict[str, Union[List[str], str]], path: str):
        """
        Create changelog fragment.
        """
        self.content = content
        self.path = path
        self.name = os.path.basename(path)

    def remove(self) -> None:
        """
        Remove changelog fragment from disk.
        """
        try:
            os.remove(self.path)
        except Exception:  # pylint: disable=broad-except
            pass

    @staticmethod
    def load(path: str) -> 'ChangelogFragment':
        """
        Load a ``ChangelogFragment`` from a file.
        """
        with open(path, 'r') as fragment_fd:
            content = yaml.safe_load(fragment_fd)

        return ChangelogFragment(content, path)

    @staticmethod
    def from_dict(data: Dict[str, Union[List[str], str]], path: str = '') -> 'ChangelogFragment':
        """
        Create a ``ChangelogFragment`` from a dictionary.
        """
        return ChangelogFragment(data, path)

    @staticmethod
    def combine(fragments: List['ChangelogFragment']) -> Dict[str, Union[List[str], str]]:
        """
        Combine fragments into a new fragment.
        """
        result: Dict[str, Union[List[str], str]] = {}

        for fragment in fragments:
            for section, content in fragment.content.items():
                if isinstance(content, list):
                    lines = result.get(section)
                    if lines is None:
                        lines = []
                        result[section] = lines
                    elif not isinstance(lines, list):
                        raise ValueError(
                            'Cannot append list to string for section "{0}"'.format(section))

                    lines.extend(content)
                else:
                    result[section] = content

        return result


class ChangelogFragmentLinter:
    # pylint: disable=too-few-public-methods
    """
    Linter for ``ChangelogFragment`` objects.
    """

    def __init__(self, config: ChangelogConfig):
        """
        Create changelog fragment linter.
        """
        self.config = config

    def _lint_section(self, errors: List[Tuple[str, int, int, str]],
                      fragment: ChangelogFragment, section: str,
                      lines: Any) -> None:
        """
        Lint a section of a changelog fragment.
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

            if section not in self.config.sections and section != self.config.trivial_section_name:
                errors.append((fragment.path, 0, 0, 'invalid section: %s' % section))

    @staticmethod
    def _lint_lines(errors: List[Tuple[str, int, int, str]],
                    fragment: ChangelogFragment, section: str,
                    lines: Any) -> None:
        """
        Lint lines of a changelog fragment.
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

    def lint(self, fragment: ChangelogFragment) -> List[Tuple[str, int, int, str]]:
        """
        Lint a ``ChangelogFragment``.

        :arg fragment: The changelog fragment to lint
        :return: A list of errors. If empty, the changelog fragment is valid.
        """
        errors: List[Tuple[str, int, int, str]] = []

        if isinstance(fragment.content, dict):  # type: ignore
            for section, lines in fragment.content.items():
                self._lint_section(errors, fragment, section, lines)
                self._lint_lines(errors, fragment, section, lines)

        else:
            errors.append((fragment.path, 0, 0,
                           'file must be a mapping not %s' % (type(fragment.content).__name__, )))

        return errors


def load_fragments(paths: PathsConfig, config: ChangelogConfig,
                   fragment_paths: Optional[List[str]] = None,
                   exceptions: Optional[List[Tuple[str, Exception]]] = None
                   ) -> List[ChangelogFragment]:
    """
    Load changelog fragments from disk.

    :arg path: Paths configuration
    :arg config: Changelog configuration
    :arg fragment_paths: List of changelog fragment paths. If not given, all will be used
    :arg exceptions: If given, exceptions during loading will be stored in this list instead
                     of being propagated
    """
    if not fragment_paths:
        fragments_dir = os.path.join(paths.changelog_dir, config.notes_dir)
        fragment_paths = [
            os.path.join(fragments_dir, path)
            for path in os.listdir(fragments_dir) if not path.startswith('.')]

    fragments: List[ChangelogFragment] = []

    for path in fragment_paths:
        try:
            fragments.append(ChangelogFragment.load(path))
        except Exception as ex:  # pylint: disable=broad-except
            if exceptions is not None:
                exceptions.append((path, ex))
            else:
                raise

    return fragments
