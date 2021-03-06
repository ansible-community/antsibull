# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Entrypoint to the antsibull-changelog script.
"""

import argparse
import os.path
import sys
import traceback

from typing import Any, List

try:
    import argcomplete
    HAS_ARGCOMPLETE = True
except ImportError:
    HAS_ARGCOMPLETE = False

from antsibull_changelog.lint import lint_changelog_yaml
from antsibull_changelog.logger import setup_logger

from ..args import get_toplevel_parser, normalize_toplevel_options
from ..lint_extra_docs import lint_collection_extra_docs_files


def run(args: List[str]) -> int:
    """
    Main program entry point.
    """
    verbosity = 0
    try:
        program_name = os.path.basename(args[0])
        parser = get_toplevel_parser(
            prog=program_name,
            description='Linting tool')

        common = argparse.ArgumentParser(add_help=False)
        common.add_argument('-v', '--verbose',
                            action='count',
                            default=0,
                            help='increase verbosity of output')

        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True

        changelog_yaml = subparsers.add_parser('changelog-yaml',
                                               parents=[common],
                                               help='changelogs/changelog.yaml linter')
        changelog_yaml.set_defaults(command=command_lint_changelog)

        changelog_yaml.add_argument('changelog_yaml_path',
                                    metavar='/path/to/changelog.yaml',
                                    help='path to changelogs/changelog.yaml')

        collection_docs = subparsers.add_parser('collection-docs',
                                                parents=[common],
                                                help='Collection extra docs linter for inclusion'
                                                     ' in docsite')
        collection_docs.set_defaults(command=command_lint_collection_docs)

        collection_docs.add_argument('collection_root_path',
                                     metavar='/path/to/collection',
                                     help='path to collection (directory that includes galaxy.yml)')

        if HAS_ARGCOMPLETE:
            argcomplete.autocomplete(parser)

        arguments = parser.parse_args(args[1:])

        normalize_toplevel_options(arguments)

        verbosity = arguments.verbose
        setup_logger(verbosity)

        return arguments.command(arguments)
    except SystemExit as e:
        return e.code
    except Exception:  # pylint: disable=broad-except
        if verbosity > 0:
            traceback.print_exc()
        else:
            print('ERROR: Uncaught exception. Run with -v to see traceback.')
        return 1


def command_lint_changelog(args: Any) -> int:
    """
    Validate a changelogs/changelog.yaml file.

    :arg args: Parsed arguments
    """
    errors = lint_changelog_yaml(args.changelog_yaml_path)

    messages = sorted(set(
        '%s:%d:%d: %s' % (error[0], error[1], error[2], error[3])
        for error in errors))

    for message in messages:
        print(message)

    return 3 if messages else 0


def command_lint_collection_docs(args: Any) -> int:
    """
    Validate docs/docsite/rst/ in a collection.

    :arg args: Parsed arguments
    """
    errors = lint_collection_extra_docs_files(args.collection_root_path)

    messages = sorted(set(
        '%s:%d:%d: %s' % (error[0], error[1], error[2], error[3])
        for error in errors))

    for message in messages:
        print(message)

    return 3 if messages else 0


def main() -> int:
    """
    Entrypoint called from the script.

    console_scripts call functions which take no parameters.  However, it's hard to test a function
    which takes no parameters so this function lightly wraps :func:`run`, which actually does the
    heavy lifting.

    :returns: A program return code.

    Return codes:
        :0: Success
        :1: Unhandled error.  See the Traceback for more information.
        :2: There was a problem with the command line arguments
        :3: Linting failed
        :4: Needs to be run on a newer version of Python
    """
    if sys.version_info < (3, 6):
        print('Needs Python 3.6 or later')
        return 4

    return run(sys.argv)
