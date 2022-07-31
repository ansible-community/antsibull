# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020

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

from antsibull_core.args import get_toplevel_parser, normalize_toplevel_options

from antsibull_docs.lint_extra_docs import lint_collection_extra_docs_files
from antsibull_docs.collection_links import lint_collection_links


def run(args: List[str]) -> int:
    """
    Main program entry point.
    """
    print(
        'WARNING: `antsibull-lint` is deprecated. Use `antsibull-changelog lint-changelog-yaml`'
        ' or `antsibull-docs lint-collection-docs` depending on your use-case.',
        file=sys.stderr)
    verbosity = 0
    try:
        program_name = os.path.basename(args[0])
        parser = get_toplevel_parser(
            prog=program_name,
            package='antsibull',
            description='Linting tool')

        common = argparse.ArgumentParser(add_help=False)
        common.add_argument('-v', '--verbose',
                            action='count',
                            default=0,
                            help='increase verbosity of output')

        subparsers = parser.add_subparsers(dest='command')
        # Make sure that our code below is used instead of the default code. Our code uses
        # parser.print_help(), which shows the deprecation messages.
        # subparsers.required = True

        changelog_yaml = subparsers.add_parser('changelog-yaml',
                                               parents=[common],
                                               help='changelogs/changelog.yaml linter. WARNING:'
                                                    ' this is deprecated; use `antsibull-changelog'
                                                    ' lint-changelog-yaml` instead!')
        changelog_yaml.set_defaults(func=command_lint_changelog)

        changelog_yaml.add_argument('changelog_yaml_path',
                                    metavar='/path/to/changelog.yaml',
                                    help='path to changelogs/changelog.yaml')

        changelog_yaml.add_argument('--no-semantic-versioning', action='store_true',
                                    help='Assume that use_semantic_versioning=false in the'
                                         ' changelog config. Do not use this for Ansible'
                                         ' collections!')

        collection_docs = subparsers.add_parser('collection-docs',
                                                parents=[common],
                                                help='Collection extra docs linter for inclusion'
                                                     ' in docsite. WARNING: this is deprecated;'
                                                     ' use `antsibull-docs lint-collection-docs`'
                                                     ' instead!')
        collection_docs.set_defaults(func=command_lint_collection_docs)

        collection_docs.add_argument('collection_root_path',
                                     metavar='/path/to/collection',
                                     help='path to collection (directory that includes galaxy.yml)')

        if HAS_ARGCOMPLETE:
            argcomplete.autocomplete(parser)

        arguments = parser.parse_args(args[1:])

        if getattr(arguments, 'func', None) is None:
            parser.print_help()
            return 2

        normalize_toplevel_options(arguments)

        verbosity = arguments.verbose
        setup_logger(verbosity)

        return arguments.func(arguments)
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
    print(
        'WARNING: `antsibull-lint changelog-yaml` is deprecated.'
        ' Use `antsibull-changelog lint-changelog-yaml` instead.',
        file=sys.stderr)

    errors = lint_changelog_yaml(
        args.changelog_yaml_path, no_semantic_versioning=args.no_semantic_versioning)

    messages = sorted(set(f'{error[0]}:{error[1]}:{error[2]}: {error[3]}' for error in errors))

    for message in messages:
        print(message)

    return 3 if messages else 0


def command_lint_collection_docs(args: Any) -> int:
    """
    Validate docs/docsite/rst/ in a collection.

    :arg args: Parsed arguments
    """
    print(
        'WARNING: `antsibull-lint collection-docs` is deprecated.'
        ' Use `antsibull-docs lint-collection-docs` instead.',
        file=sys.stderr)

    errors = lint_collection_extra_docs_files(args.collection_root_path)
    errors.extend(lint_collection_links(args.collection_root_path))

    messages = sorted(set(f'{error[0]}:{error[1]}:{error[2]}: {error[3]}' for error in errors))

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


if __name__ == '__main__':
    sys.exit(main())
