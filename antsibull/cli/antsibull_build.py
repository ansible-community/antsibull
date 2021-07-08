# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Entrypoint to the antsibull-build tool."""

import argparse
import os.path
import sys
from typing import List

import twiggy
from packaging.version import Version as PypiVer

from ..logging import log, initialize_app_logging
initialize_app_logging()

# We have to call initialize_app_logging() before these imports so that the log object is configured
# correctly before other antisbull modules make copies of it.
# pylint: disable=wrong-import-position
from .. import app_context  # noqa: E402
from ..args import (  # noqa: E402
    InvalidArgumentError, get_toplevel_parser, normalize_toplevel_options
)
from ..build_collection import build_collection_command  # noqa: E402
from ..build_ansible_commands import (  # noqa: E402
    build_single_command, build_multiple_command, rebuild_single_command,
)
from ..build_changelog import build_changelog  # noqa: E402
from ..config import load_config  # noqa: E402
from ..new_ansible import new_ansible_command  # noqa: E402
# pylint: enable=wrong-import-position


mlog = log.fields(mod=__name__)

DEFAULT_FILE_BASE = 'ansible'
DEFAULT_PIECES_FILE = f'{DEFAULT_FILE_BASE}.in'

ARGS_MAP = {'new-ansible': new_ansible_command,
            'single': build_single_command,
            'multiple': build_multiple_command,
            'collection': build_collection_command,
            'changelog': build_changelog,
            'rebuild-single': rebuild_single_command,
            # Old names, deprecated
            'new-acd': new_ansible_command,
            'build-single': build_single_command,
            'build-multiple': build_multiple_command,
            'build-collection': build_collection_command,
            }


def _normalize_build_options(args: argparse.Namespace) -> None:
    if not os.path.isdir(args.data_dir):
        raise InvalidArgumentError(f'{args.data_dir} must be an existing directory')


def _normalize_build_write_data_options(args: argparse.Namespace) -> None:
    if args.command not in (
            'new-ansible', 'single', 'rebuild-single', 'multiple', 'changelog',
            'new-acd', 'build-single', 'build-multiple'):
        return

    if args.dest_data_dir is None:
        args.dest_data_dir = args.data_dir

    if not os.path.isdir(args.dest_data_dir):
        raise InvalidArgumentError(f'{args.dest_data_dir} must be an existing directory')


def _normalize_new_release_options(args: argparse.Namespace) -> None:
    flog = mlog.fields(func='_normalize_new_release_options')

    if args.command == 'new-acd':
        flog.warning('The new-acd command is deprecated.  Use `new-ansible` instead.')
        args.command = 'new-ansible'

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


def _normalize_release_build_options(args: argparse.Namespace) -> None:
    flog = mlog.fields(func='_normalize_release_build_options')

    if args.command == 'build-single':
        flog.warning('The build-single command is deprecated.  Use `single` instead.')
        args.command = 'single'

    if args.command == 'build-multiple':
        flog.warning('The build-multiple command is deprecated.  Use `multiple` instead.')
        args.command = 'multiple'

    if args.command not in ('single', 'multiple', 'rebuild-single'):
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

    if args.command in ('single', 'multiple'):
        if not os.path.isdir(args.sdist_dir):
            raise InvalidArgumentError(f'{args.sdist_dir} must be an existing directory')


def _normalize_release_rebuild_options(args: argparse.Namespace) -> None:
    if args.command not in ('rebuild-single', ):
        return

    deps_filename = os.path.join(args.data_dir, args.deps_file)
    if not os.path.isfile(deps_filename):
        raise InvalidArgumentError(f'The dependency file, {deps_filename} must already exist.')


def _normalize_collection_build_options(args: argparse.Namespace) -> None:
    flog = mlog.fields(func='_normalize_collection_build_options')

    if args.command == 'build-collection':
        flog.warning('The build-collection command is deprecated.  Use `collection` instead.')
        args.command = 'collection'

    if args.command != 'collection':
        return

    if args.deps_file is None:
        args.deps_file = DEFAULT_FILE_BASE + f'{args.ansible_version}.deps'

    if not os.path.isdir(args.collection_dir):
        raise InvalidArgumentError(f'{args.collection_dir} must be an existing directory')


def parse_args(program_name: str, args: List[str]) -> argparse.Namespace:
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
    cache_parser.add_argument('--collection-cache', default=None,
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

    parser = get_toplevel_parser(prog=program_name,
                                 description='Script to manage building Ansible')

    subparsers = parser.add_subparsers(title='Subcommands', dest='command',
                                       help='for help use antsibull-build SUBCOMMANDS -h')
    subparsers.required = True

    new_parser = subparsers.add_parser('new-ansible', parents=[build_write_data_parser],
                                       description='Generate a new build description from the'
                                       ' latest available versions of ansible-base and the'
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

    build_single_parser = subparsers.add_parser('single',
                                                parents=[build_write_data_parser, cache_parser,
                                                         build_step_parser, feature_freeze_parser],
                                                description='Build a single-file Ansible')
    build_single_parser.add_argument('--sdist-dir', default='.',
                                     help='Directory to write the generated sdist tarball to')
    build_single_parser.add_argument('--debian', action='store_true',
                                     help='Include Debian/Ubuntu packaging files in'
                                     ' the resulting output directory')

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
    build_parser.add_argument('--collection-dir', default='.',
                              help='Directory to write collection to')

    subparsers.add_parser('changelog',
                          parents=[build_write_data_parser, cache_parser],
                          description='Build the Ansible changelog')

    # Backwards compat
    subparsers.add_parser('new-acd', add_help=False, parents=[new_parser])
    subparsers.add_parser('build-single', add_help=False, parents=[build_single_parser])
    subparsers.add_parser('build-multiple', add_help=False, parents=[build_multiple_parser])
    subparsers.add_parser('build-collection', add_help=False, parents=[collection_parser])

    args: argparse.Namespace = parser.parse_args(args)

    # Validation and coercion
    normalize_toplevel_options(args)
    _normalize_build_options(args)
    _normalize_build_write_data_options(args)
    _normalize_new_release_options(args)
    _normalize_release_build_options(args)
    _normalize_release_rebuild_options(args)
    _normalize_collection_build_options(args)

    return args


def run(args: List[str]) -> int:
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
        args: argparse.Namespace = parse_args(program_name, args[1:])
    except InvalidArgumentError as e:
        print(e)
        return 2

    cfg = load_config(args.config_file)
    flog.fields(config=cfg).info('Config loaded')

    context_data = app_context.create_contexts(args=args, cfg=cfg)
    with app_context.app_and_lib_context(context_data) as (app_ctx, dummy_):
        twiggy.dict_config(app_ctx.logging_cfg.dict())
        flog.debug('Set logging config')

        return ARGS_MAP[args.command]()


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
