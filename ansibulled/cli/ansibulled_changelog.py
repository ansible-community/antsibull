# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Entrypoint to the ansibulled-changelog script.
"""

import argparse
import datetime
import logging
import os
import sys
import traceback

from typing import cast, Any, List, Optional, Tuple, Union

try:
    import argcomplete
    HAS_ARGCOMPLETE = True
except ImportError:
    HAS_ARGCOMPLETE = False

from ..changelog.ansible import get_ansible_release
from ..changelog.changelog_generator import generate_changelog
from ..changelog.changes import load_changes, add_release
from ..changelog.config import PathsConfig, ChangelogConfig
from ..changelog.fragment import load_fragments, ChangelogFragment, ChangelogFragmentLinter
from ..changelog.plugins import load_plugins, PluginDescription
from ..changelog.utils import ChangelogError, LOGGER, load_galaxy_metadata


def set_paths(force: Union[str, None] = None) -> PathsConfig:
    """
    Create ``PathsConfig``.

    :arg force: If ``True``, create a collection path config for the given path.
                Otherwise, detect configuration.
    """
    if force:
        return PathsConfig.force_collection(force)

    try:
        return PathsConfig.detect()
    except ValueError:
        raise ChangelogError(
            "Only the 'init' and 'lint-changelog' commands can be used outside an "
            "Ansible checkout and outside a collection repository.\n")


def create_argparser(program_name: str) -> argparse.ArgumentParser:
    """
    Create CLI argument parser.
    """
    parser = argparse.ArgumentParser(
        prog=program_name,
        description='Changelog generator and linter.')

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('-v', '--verbose',
                        action='count',
                        default=0,
                        help='increase verbosity of output')

    subparsers = parser.add_subparsers(metavar='COMMAND')

    init_parser = subparsers.add_parser('init',
                                        parents=[common],
                                        help='set up changelog infrastructure for collection')
    init_parser.set_defaults(func=command_init)
    init_parser.add_argument('root',
                             metavar='COLLECTION_ROOT',
                             help='path to collection root')

    lint_parser = subparsers.add_parser('lint',
                                        parents=[common],
                                        help='check changelog fragments for syntax errors')
    lint_parser.set_defaults(func=command_lint)
    lint_parser.add_argument('fragments',
                             metavar='FRAGMENT',
                             nargs='*',
                             help='path to fragment to test')

    release_parser = subparsers.add_parser('release',
                                           parents=[common],
                                           help='add a new release to the change metadata')
    release_parser.set_defaults(func=command_release)
    release_parser.add_argument('--version',
                                help='override release version')
    release_parser.add_argument('--codename',
                                help='override/set release codename')
    release_parser.add_argument('--date',
                                default=str(datetime.date.today()),
                                help='override release date')
    release_parser.add_argument('--reload-plugins',
                                action='store_true',
                                help='force reload of plugin cache')

    generate_parser = subparsers.add_parser('generate',
                                            parents=[common],
                                            help='generate the changelog')
    generate_parser.set_defaults(func=command_generate)
    generate_parser.add_argument('--reload-plugins',
                                 action='store_true',
                                 help='force reload of plugin cache')

    if HAS_ARGCOMPLETE:
        argcomplete.autocomplete(parser)

    return parser


def setup_logger(verbosity: int) -> None:
    """
    Setup logger.
    """
    formatter = logging.Formatter('%(levelname)s %(message)s')

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.WARN)

    if verbosity > 2:
        LOGGER.setLevel(logging.DEBUG)
    elif verbosity > 1:
        LOGGER.setLevel(logging.INFO)
    elif verbosity > 0:
        LOGGER.setLevel(logging.WARN)


def run(args: List[str]) -> int:
    """
    Main program entry point.
    """
    verbosity = 0
    try:
        program_name = os.path.basename(args[0])
        parser = create_argparser(program_name)

        arguments = parser.parse_args(args[1:])

        if getattr(arguments, 'func', None) is None:
            parser.print_help()
            return 2

        verbosity = arguments.verbose
        setup_logger(verbosity)

        return arguments.func(arguments)
    except ChangelogError as e:
        LOGGER.error(str(e))
        if verbosity > 2:
            traceback.print_exc()
        return 5
    except SystemExit as e:
        return e.code
    except Exception:  # pylint: disable=broad-except
        if verbosity > 0:
            traceback.print_exc()
        else:
            print('ERROR: Uncaught exception. Run with -v to see traceback.')
        return 1


def command_init(args: Any) -> int:
    """
    Initialize a changelog config.

    :arg args: Parsed arguments
    """
    root: str = args.root

    paths = set_paths(force=root)

    LOGGER.debug('Checking "{}" for existance', paths.galaxy_path)
    if not os.path.exists(cast(str, paths.galaxy_path)):
        LOGGER.error('The file galaxy.yml does not exists in the collection root!')
        return 5
    LOGGER.debug('Checking "{}" for existance', paths.config_path)
    if os.path.exists(paths.config_path):
        LOGGER.error('A configuration file already exists at "{}"!', paths.config_path)
        return 5

    galaxy = load_galaxy_metadata(paths)

    config = ChangelogConfig.default(
        title='{0}.{1}'.format(galaxy['namespace'].title(), galaxy['name'].title()),
        is_collection=True,
    )

    fragments_dir = os.path.join(paths.changelog_dir, config.notes_dir)
    try:
        os.makedirs(fragments_dir, exist_ok=True)
        print('Created fragments directory "{0}"'.format(fragments_dir))
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.error('Cannot create fragments directory "{}"', fragments_dir)
        LOGGER.info('Exception: {}', str(exc))
        return 5

    try:
        config.store(paths.config_path)
        print('Created config file "{0}"'.format(paths.config_path))
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.error('Cannot create config file "{}"', paths.config_path)
        LOGGER.info('Exception: {}', str(exc))
        return 5

    return 0


def command_release(args: Any) -> int:
    """
    Add a new release to a changelog.

    :arg args: Parsed arguments
    """
    paths = set_paths()

    version: Union[str, None] = args.version
    codename: Union[str, None] = args.codename
    date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
    reload_plugins: bool = args.reload_plugins

    config = ChangelogConfig.load(paths.config_path, paths.galaxy_path is not None)

    flatmap = True
    if config.is_collection:
        galaxy = load_galaxy_metadata(paths)
        flatmap = galaxy.get('type', '') == 'flatmap'

    if not version or not codename:
        if not config.is_collection:
            # Both version and codename are required for Ansible (Base)
            try:
                version, codename = get_ansible_release()
            except ValueError:
                LOGGER.error('Cannot import ansible.release to determine version and codename')
                return 5

        elif not version:
            # Codename is not required for collections, only version is
            try:
                galaxy = load_galaxy_metadata(paths)
                version = galaxy['version']
                if not isinstance(version, str):
                    raise Exception('Version in galaxy.yml is not a string')
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.error('Error while extracting version from galaxy.yml: {}', str(exc))
                return 5

    changes = load_changes(paths, config)
    plugins = load_plugins(paths=paths, version=version, force_reload=reload_plugins)
    fragments = load_fragments(paths, config)
    add_release(config, changes, plugins, fragments, version, codename, date)
    generate_changelog(paths, config, changes, plugins, fragments, flatmap=flatmap)

    return 0


def command_generate(args: Any) -> int:
    """
    (Re-)generate the reStructuredText version of the changelog.

    :arg args: Parsed arguments
    """
    paths = set_paths()

    reload_plugins: bool = args.reload_plugins

    config = ChangelogConfig.load(paths.config_path, paths.galaxy_path is not None)

    flatmap = True
    if config.is_collection:
        galaxy = load_galaxy_metadata(paths)
        flatmap = galaxy.get('type', '') == 'flatmap'

    changes = load_changes(paths, config)
    if not changes.has_release:
        print('Cannot create changelog when not at least one release has been added.')
        return 5
    plugins: Optional[List[PluginDescription]]
    if reload_plugins:
        plugins = load_plugins(
            paths=paths, version=changes.latest_version, force_reload=reload_plugins)
    else:
        plugins = None
    fragments = load_fragments(paths, config)
    generate_changelog(paths, config, changes, plugins, fragments, flatmap=flatmap)

    return 0


def command_lint(args: Any) -> int:
    """
    Lint changelog fragments.

    :arg args: Parsed arguments
    """
    paths = set_paths()

    fragment_paths: List[str] = args.fragments

    config = ChangelogConfig.load(paths.config_path, paths.galaxy_path is not None)

    exceptions: List[Tuple[str, Exception]] = []
    fragments = load_fragments(paths, config, fragment_paths, exceptions)
    return lint_fragments(config, fragments, exceptions)


def lint_fragments(config: ChangelogConfig, fragments: List[ChangelogFragment],
                   exceptions: List[Tuple[str, Exception]]) -> int:
    """
    Lint a given set of changelog fragment objects.

    :arg config: The configuration
    :arg fragments: The loaded fragments
    :arg exceptions: Exceptions from loading the fragments
    """
    linter = ChangelogFragmentLinter(config)

    errors = [(ex[0], 0, 0, 'yaml parsing error') for ex in exceptions]

    for fragment in fragments:
        errors += linter.lint(fragment)

    messages = sorted(set(
        '%s:%d:%d: %s' % (os.path.relpath(error[0]), error[1], error[2], error[3])
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
        :3: Found invalid changelog fragments
        :4: Needs to be run on a newer version of Python
        :5: Problem occured which prevented the execution of the command
    """
    if sys.version_info < (3, 6):
        print('Needs Python 3.6 or later')
        return 4

    return run(sys.argv)
