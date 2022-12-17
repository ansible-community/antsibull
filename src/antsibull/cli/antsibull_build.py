# Author: Toshio Kuratomi <tkuratom@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020
"""Entrypoint to the antsibull-build tool."""

from __future__ import annotations

import argparse
import os.path
import sys

import twiggy  # type: ignore[import]
from packaging.version import Version as PypiVer

from antsibull_core.logging import log, initialize_app_logging
initialize_app_logging()

# We have to call initialize_app_logging() before these imports so that the log object is configured
# correctly before other antisbull modules make copies of it.
# pylint: disable=wrong-import-position
from antsibull_core import app_context  # noqa: E402
from antsibull_core.args import (  # noqa: E402
    InvalidArgumentError, get_toplevel_parser, normalize_toplevel_options
)
from antsibull_core.config import ConfigError, load_config  # noqa: E402

from ..build_collection import build_collection_command  # noqa: E402
from ..build_ansible_commands import (  # noqa: E402
    prepare_command, build_single_command, build_multiple_command, rebuild_single_command,
)
from ..build_changelog import build_changelog  # noqa: E402
from ..dep_closure import validate_dependencies_command  # noqa: E402
from ..new_ansible import new_ansible_command  # noqa: E402
from ..tagging import validate_tags_command, validate_tags_file_command  # noqa: E402
# pylint: enable=wrong-import-position


mlog = log.fields(mod=__name__)

DEFAULT_FILE_BASE = 'ansible'
DEFAULT_PIECES_FILE = f'{DEFAULT_FILE_BASE}.in'

ARGS_MAP = {'new-ansible': new_ansible_command,
            'prepare': prepare_command,
            'single': build_single_command,
            'multiple': build_multiple_command,
            'collection': build_collection_command,
            'changelog': build_changelog,
            'rebuild-single': rebuild_single_command,
            'validate-deps': validate_dependencies_command,
            'validate-tags': validate_tags_command,
            'validate-tags-file': validate_tags_file_command,
            }


def _normalize_commands(args: argparse.Namespace) -> None:  # pylint: disable=unused-argument
    # If command names change and old ones need to be deprecated, do that here.
    # Check out the git history for examples.
    pass


def _normalize_build_options(args: argparse.Namespace) -> None:
    if args.command in ('validate-deps', 'validate-tags', 'validate-tags-file'):
        return

    if not os.path.isdir(args.data_dir):
        raise InvalidArgumentError(f'{args.data_dir} must be an existing directory')


def _normalize_build_write_data_options(args: argparse.Namespace) -> None:
    if args.command not in (
            'new-ansible', 'prepare', 'single', 'rebuild-single', 'multiple', 'changelog'):
        return

    if args.dest_data_dir is None:
        args.dest_data_dir = args.data_dir

    if not os.path.isdir(args.dest_data_dir):
        raise InvalidArgumentError(f'{args.dest_data_dir} must be an existing directory')


def _normalize_new_release_options(args: argparse.Namespace) -> None:
    if args.command != 'new-ansible':
        return

    if args.pieces_file is None:
        args.pieces_file = DEFAULT_PIECES_FILE

    pieces_path = os.path.join(args.data_dir, args.pieces_file)
    if not os.path.isfile(pieces_path):
        raise InvalidArgumentError(f'The pieces file, {pieces_path}, must already'
                                   ' exist. It should contain one namespace.collection'
                                   ' per line')

    if args.build_file is None:
        basename = os.path.basename(os.path.splitext(args.pieces_file)[0])
        if args.ansible_version.major > 2:
            args.build_file = (
                f'{basename}-{args.ansible_version.major}.build'
            )
        else:
            args.build_file = (
                f'{basename}-{args.ansible_version.major}.{args.ansible_version.minor}.build'
            )


def _check_release_build_directories(args: argparse.Namespace) -> None:
    if args.command in ('single', 'multiple', 'rebuild-single'):
        if not os.path.isdir(args.sdist_dir):
            raise InvalidArgumentError(f'{args.sdist_dir} must be an existing directory')

    if args.command in ('rebuild-single', ):
        if args.sdist_src_dir is not None and os.path.exists(args.sdist_src_dir):
            raise InvalidArgumentError(f'{args.sdist_src_dir} must not exist')


def _normalize_release_build_options(args: argparse.Namespace) -> None:
    if args.command not in ('prepare', 'single', 'multiple', 'rebuild-single'):
        return

    compat_version_part = (
        f'{args.ansible_version.major}' if args.ansible_version.major > 2
        else f'{args.ansible_version.major}.{args.ansible_version.minor}'
    )

    if args.build_file is None:
        args.build_file = DEFAULT_FILE_BASE + f'-{compat_version_part}.build'

    build_filename = os.path.join(args.data_dir, args.build_file)
    if not os.path.isfile(build_filename):
        raise InvalidArgumentError(f'The build file, {build_filename} must already exist.'
                                   ' It should contains one namespace.collection and range'
                                   ' of versions per line')

    if args.deps_file is None:
        version_suffix = f'-{compat_version_part}'
        basename = os.path.basename(os.path.splitext(args.build_file)[0])
        if basename.endswith(version_suffix):
            basename = basename[:-len(version_suffix)]

        args.deps_file = f'{basename}-{args.ansible_version}.deps'

    if args.command != 'multiple' and args.tags_file:
        _check_tags_file(args)

    if args.command in ('prepare', 'single') and args.galaxy_file is None:
        version_suffix = f'-{compat_version_part}'
        basename = os.path.basename(os.path.splitext(args.build_file)[0])
        if basename.endswith(version_suffix):
            basename = basename[:-len(version_suffix)]

        args.galaxy_file = f'{basename}-{args.ansible_version}.yaml'

    _check_release_build_directories(args)


def _check_tags_file(args: argparse.Namespace) -> None:
    if args.tags_file == "DEFAULT":
        args.tags_file = f'{DEFAULT_FILE_BASE}-{args.ansible_version}-tags.yaml'
    tags_path = os.path.join(args.data_dir, args.tags_file)

    if args.command == 'rebuild-single' and not os.path.isfile(tags_path):
        raise InvalidArgumentError(f'{tags_path} does not exist!')


def _normalize_release_rebuild_options(args: argparse.Namespace) -> None:
    if args.command not in ('rebuild-single', 'validate-tags'):
        return

    deps_filename = os.path.join(args.data_dir, args.deps_file)
    if not os.path.isfile(deps_filename):
        raise InvalidArgumentError(f'The dependency file, {deps_filename} must already exist.')


def _normalize_collection_build_options(args: argparse.Namespace) -> None:
    if args.command != 'collection':
        return

    if args.deps_file is None:
        args.deps_file = DEFAULT_FILE_BASE + f'{args.ansible_version}.deps'

    if not os.path.isdir(args.collection_dir):
        raise InvalidArgumentError(f'{args.collection_dir} must be an existing directory')


def _normalize_validate_tags_options(args: argparse.Namespace) -> None:
    if args.command not in ('validate-tags',):
        return
    if args.deps_file is None:
        args.deps_file = DEFAULT_FILE_BASE + f'-{args.ansible_version}.deps'


def _normalize_validate_tags_file_options(args: argparse.Namespace) -> None:
    if args.command not in ('validate-tags-file',):
        return
    if not os.path.exists(args.tags_file):
        raise InvalidArgumentError(f"{args.tags_file} does not exist!")


def parse_args(program_name: str, args: list[str]) -> argparse.Namespace:
    """
    Parse and coerce the command line arguments.

    :arg program_name: The name of the program
    :arg args: A list of the command line arguments
    :returns: A :python:`argparse.Namespace`
    :raises InvalidArgumentError: Whenever there's something wrong with the arguments.
    """
    build_parser = argparse.ArgumentParser(add_help=False)
    build_parser.add_argument('ansible_version', type=PypiVer,
                              help='The X.Y.Z version of Ansible that this will be for')
    build_parser.add_argument('--data-dir', default='.',
                              help='Directory to read .build and .deps files from')

    build_write_data_parser = argparse.ArgumentParser(add_help=False, parents=[build_parser])
    build_write_data_parser.add_argument('--dest-data-dir', default=None,
                                         help='Directory to write .build and .deps files to,'
                                         ' as well as changelog and porting guide if applicable.'
                                         '  Defaults to --data-dir')
    cache_parser = argparse.ArgumentParser(add_help=False)
    cache_parser.add_argument('--collection-cache', default=argparse.SUPPRESS,
                              help='Directory of cached collection tarballs.  Will be'
                              ' used if a collection tarball to be downloaded exists'
                              ' in here, and will be populated when downloading new'
                              ' tarballs.')

    build_step_parser = argparse.ArgumentParser(add_help=False)
    build_step_parser.add_argument('--build-file', default=None,
                                   help='File containing the list of collections with version'
                                   ' ranges.  This is considered to be relative to'
                                   ' --build-data-dir.  The default is'
                                   ' $DEFAULT_FILE_BASE-X.Y.build')
    build_step_parser.add_argument('--deps-file', default=None,
                                   help='File which will be written containing the list of'
                                   ' collections at versions which were included in this version'
                                   ' of Ansible.  This is considered to be relative to'
                                   ' --build-data-dir.  The default is'
                                   ' $BASENAME_OF_BUILD_FILE-X.Y.Z.deps')

    feature_freeze_parser = argparse.ArgumentParser(add_help=False)
    feature_freeze_parser.add_argument('--feature-frozen', action='store_true',
                                       help='If this is given, then do not allow collections whose'
                                       ' version implies there are new features.')

    galaxy_file_parser = argparse.ArgumentParser(add_help=False)
    galaxy_file_parser.add_argument('--galaxy-file', default=None,
                                    help='Galaxy galaxy-requirements.yaml style file which will be'
                                    ' written containing the list of collections at versions which'
                                    ' were included in this version of Ansible.  This is'
                                    ' considered to be relative to --build-data-dir.  The default'
                                    ' is $BASENAME_OF_BUILD_FILE-X.Y.Z.yaml')

    parser = get_toplevel_parser(prog=program_name,
                                 package='antsibull',
                                 description='Script to manage building Ansible')

    subparsers = parser.add_subparsers(title='Subcommands', dest='command',
                                       help='for help use antsibull-build SUBCOMMANDS -h')
    subparsers.required = True

    new_parser = subparsers.add_parser('new-ansible', parents=[build_write_data_parser],
                                       description='Generate a new build description from the'
                                       ' latest available versions of ansible-core and the'
                                       ' included collections')
    new_parser.add_argument('--pieces-file', default=None,
                            help='File containing a list of collections to include.  This is'
                            ' considered to be relative to --data-dir.  The default is'
                            f' {DEFAULT_PIECES_FILE}')
    new_parser.add_argument('--build-file', default=None,
                            help='File which will be written which contains the list'
                            ' of collections with version ranges.  This is considered to be'
                            ' relative to --dest-data-dir.  The default is'
                            ' $BASENAME_OF_PIECES_FILE-X.Y.build')
    new_parser.add_argument('--allow-prereleases', action='store_true', default=False,
                            help='Allow prereleases of collections to be included in the build'
                            ' file')

    prepare_parser = subparsers.add_parser(
        'prepare',
        parents=[
            build_write_data_parser,
            build_step_parser,
            feature_freeze_parser,
            galaxy_file_parser,
        ],
        description='Collect dependencies for an Ansible release',
    )
    prepare_parser.add_argument(
        '--tags-file', nargs='?', const='DEFAULT',
        help='Whether to include a tags data file in --dest-data-dir.'
             ' By default, the tags data file is stored in --dest-data-dir'
             f' as {DEFAULT_FILE_BASE}-X.Y.Z-tags.yaml.'
             ' --tags-file takes an optional argument to change the filename.'
    )

    build_single_parser = subparsers.add_parser('single',
                                                parents=[
                                                    build_write_data_parser, cache_parser,
                                                    build_step_parser, feature_freeze_parser,
                                                    galaxy_file_parser,
                                                ],
                                                description='Build a single-file Ansible'
                                                ' [deprecated]')
    build_single_parser.add_argument('--sdist-dir', default='.',
                                     help='Directory to write the generated sdist tarball to')
    build_single_parser.add_argument('--debian', action='store_true',
                                     help='Include Debian/Ubuntu packaging files in'
                                     ' the resulting output directory')
    build_single_parser.add_argument(
        '--tags-file', nargs='?', const='DEFAULT',
        help='Whether to include a tags data file in --dest-data-dir and the sdist.'
             ' By default, the tags data file is stored in --dest-data-dir'
             f' as {DEFAULT_FILE_BASE}-X.Y.Z-tags.yaml.'
             ' --tags-file takes an optional argument to change the filename.'
             " The tags data file in the sdist is always named 'tags.yaml'"
    )

    rebuild_single_parser = subparsers.add_parser('rebuild-single',
                                                  parents=[build_write_data_parser, cache_parser,
                                                           build_step_parser],
                                                  description='Rebuild a single-file Ansible from'
                                                              ' a dependency file')
    rebuild_single_parser.add_argument('--sdist-dir', default='.',
                                       help='Directory to write the generated sdist tarball to')
    rebuild_single_parser.add_argument('--debian', action='store_true',
                                       help='Include Debian/Ubuntu packaging files in'
                                       ' the resulting output directory')
    rebuild_single_parser.add_argument('--sdist-src-dir',
                                       help='Copy the files from which the source distribution is'
                                       ' created to the specified directory. This is mainly useful'
                                       ' for debugging antsibull-build')

    rebuild_single_parser.add_argument(
        '--tags-file', nargs='?', const='DEFAULT',
        help='Whether to include a tags data file in the sdist.'
             ' By default, the tags data file is stored in --data-dir'
             f' as {DEFAULT_FILE_BASE}-X.Y.Z-tags.yaml.'
             ' --tags-file takes an optional argument to change the filename.'
             " The tags data file in the sdist is always named 'tags.yaml'"
    )
    build_multiple_parser = subparsers.add_parser('multiple',
                                                  parents=[build_write_data_parser, cache_parser,
                                                           build_step_parser,
                                                           feature_freeze_parser],
                                                  description='Build a multi-file Ansible')
    build_multiple_parser.add_argument('--sdist-dir', default='.',
                                       help='Directory to write the generated sdist tarballs to')

    collection_parser = subparsers.add_parser('collection',
                                              parents=[build_parser],
                                              description='Build a collection which will'
                                              ' install Ansible')
    collection_parser.add_argument('--deps-file', default=None,
                                   help='File which contains the list of collections and'
                                   ' versions which were included in this version of Ansible.'
                                   '  This is considered to be relative to --data-dir.'
                                   f'  The default is {DEFAULT_FILE_BASE}-X.Y.Z.deps')
    collection_parser.add_argument('--collection-dir', default='.',
                                   help='Directory to write collection to')

    subparsers.add_parser('changelog',
                          parents=[build_write_data_parser, cache_parser],
                          description='Build the Ansible changelog')

    validate_deps = subparsers.add_parser('validate-deps',
                                          description='Validate collection dependencies')

    validate_deps.add_argument('collection_root',
                               help='Path to a ansible_collections directory containing a'
                               ' collection tree to check.')

    validate_tags = subparsers.add_parser(
        'validate-tags',
        parents=[build_parser],
        description="Ensure that collection versions in an Ansible release are tagged"
                    " in collections' respective git repositories."
    )
    validate_tags.add_argument(
        '--deps-file',
        default=None,
        help='File which contains the list of collections and'
        ' versions which were included in this version of Ansible.'
        '  This is considered to be relative to --data-dir.'
        f'  The default is {DEFAULT_FILE_BASE}-X.Y.Z.deps',
    )
    validate_tags.add_argument(
        '-o', '--output',
        help='Path to output a collection tag data file.'
             ' If this is ommited, no tag data will be written'
    )

    validate_tags_file = subparsers.add_parser(
        'validate-tags-file',
        description="Ensure that collection versions in an Ansible release are tagged"
                    " in collections' respective git repositories."
                    " This validates the tags file generated by"
                    " the 'validate-tags' subcommand."
        )
    validate_tags_file.add_argument('tags_file')

    parsed_args: argparse.Namespace = parser.parse_args(args)

    # Validation and coercion
    normalize_toplevel_options(parsed_args)
    _normalize_commands(parsed_args)
    _normalize_build_options(parsed_args)
    _normalize_build_write_data_options(parsed_args)
    _normalize_new_release_options(parsed_args)
    _normalize_release_build_options(parsed_args)
    _normalize_validate_tags_options(parsed_args)
    _normalize_release_rebuild_options(parsed_args)
    _normalize_collection_build_options(parsed_args)
    _normalize_validate_tags_file_options(parsed_args)

    return parsed_args


def run(args: list[str]) -> int:
    """
    Run the program.

    :arg args: A list of command line arguments.  Typically :python:`sys.argv`.
    :returns: A program return code.  0 for success, integers for any errors.  These are documented
        in :func:`main`.
    """
    flog = mlog.fields(func='run')
    flog.fields(raw_args=args).info('Enter')

    program_name = os.path.basename(args[0])
    try:
        parsed_args: argparse.Namespace = parse_args(program_name, args[1:])
    except InvalidArgumentError as e:
        print(e)
        return 2

    try:
        cfg = load_config(parsed_args.config_file)
        flog.fields(config=cfg).info('Config loaded')
    except ConfigError as e:
        print(e)
        return 2

    context_data = app_context.create_contexts(args=parsed_args, cfg=cfg)
    with app_context.app_and_lib_context(context_data) as (app_ctx, dummy_):
        twiggy.dict_config(app_ctx.logging_cfg.dict())
        flog.debug('Set logging config')

        flog.fields(command=parsed_args.command).info('Action')
        return ARGS_MAP[parsed_args.command]()


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
        :3: version in an input file does not match with the version specified on the command line
        :4: Needs to be run on a newer version of Python
    """
    return run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
