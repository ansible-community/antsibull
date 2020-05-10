# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Entrypoint to the ansibulled-changelog script."""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import argparse
import logging
import sys

try:
    import argcomplete  # pyre-ignore
except ImportError:
    argcomplete = None

from ..changelog.lint import lint_changelog_yaml
from ..changelog.utils import LOGGER


def main():
    """Main program entry point."""
    parser = argparse.ArgumentParser(description='changelogs/changelog.yaml linter')

    parser.add_argument('-v', '--verbose',
                        action='count',
                        default=0,
                        help='increase verbosity of output')

    parser.add_argument('changelog_yaml_path',
                        metavar='/path/to/changelog.yaml',
                        help='path to changelogs/changelog.yaml')

    if argcomplete:
        argcomplete.autocomplete(parser)

    formatter = logging.Formatter('%(levelname)s %(message)s')

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.WARN)

    args = parser.parse_args()

    if args.verbose > 2:
        LOGGER.setLevel(logging.DEBUG)
    elif args.verbose > 1:
        LOGGER.setLevel(logging.INFO)
    elif args.verbose > 0:
        LOGGER.setLevel(logging.WARN)

    command_lint_changelog(args)


def command_lint_changelog(args):
    """
    :type args: any
    """
    errors = lint_changelog_yaml(args.changelog_yaml_path)

    messages = sorted(set(
        '%s:%d:%d: %s' % (error[0], error[1], error[2], error[3])
        for error in errors))

    for message in messages:
        print(message)
