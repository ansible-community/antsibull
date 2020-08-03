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

from .. import app_context
from ..app_logging import log
from ..args import InvalidArgumentError, get_common_parser, normalize_common_options
from ..config import load_config
from ..new_ansible import new_ansible_command
from ..build_collection import build_collection_command
from ..build_ansible_commands import build_single_command, build_multiple_command
from ..build_changelog import build_changelog


mlog = log.fields(mod=__name__)

DEFAULT_FILE_BASE = 'ansible'
DEFAULT_PIECES_FILE = f'{DEFAULT_FILE_BASE}.in'

ARGS_MAP = {'new-ansible': new_ansible_command,
            'single': build_single_command,
            'multiple': build_multiple_command,
            'collection': build_collection_command,
            'changelog': build_changelog,
            # Old names, deprecated
            'new-acd': new_ansible_command,
            'build-single': build_single_command,
            'build-multiple': build_multiple_command,
            'build-collection': build_collection_command,
            }


def _normalize_build_options(args: argparse.Namespace) -> None:
    args.dest_dir = os.path.expanduser(os.path.expandvars(args.dest_dir))
    if not os.path.isdir(args.dest_dir):
        raise InvalidArgumentError(f'{args.dest_dir} must be an existing directory')


def _normalize_new_release_options(args: argparse.Namespace) -> None:
    flog = mlog.fields(func='_normalize_new_release_options')

    if args.command == 'new-acd':
        flog.warning('The new-acd command is deprecated.  Use `new-ansible` instead.')
        args.command = 'new-ansible'

    if args.command != 'new-ansible':
        return

    if args.pieces_file is None:
        args.pieces_file = os.path.join(args.dest_dir, DEFAULT_PIECES_FILE)

    if not os.path.isfile(args.pieces_file):
        raise InvalidArgumentError(f'The pieces file, {args.pieces_file}, must already'
                                   ' exist. It should contain one namespace.collection'
                                   ' per line')

    if args.build_file is None:
        basename = os.path.basename(os.path.splitext(args.pieces_file)[0])
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

    if args.command not in ('single', 'multiple'):
        return

    if args.build_file is None:
        args.build_file = (DEFAULT_FILE_BASE
                           + f'-{args.ansible_version.major}.{args.ansible_version.minor}.build')

    if not os.path.isfile(args.build_file):
        raise InvalidArgumentError(f'The build file, {args.build_file} must already exist.'
                                   ' It should contains one namespace.collection and range'
                                   ' of versions per line')

    if args.deps_file is None:
        major_minor = f'-{args.ansible_version.major}.{args.ansible_version.minor}'
        basename = os.path.basename(os.path.splitext(args.build_file)[0])
        if basename.endswith(major_minor):
            basename = basename[:-len(major_minor)]

        args.deps_file = f'{basename}-{args.ansible_version}.deps'


def _normalize_collection_build_options(args: argparse.Namespace) -> None:
    flog = mlog.fields(func='_normalize_collection_build_options')

    if args.command == 'build-collection':
        flog.warning('The build-collection command is deprecated.  Use `collection` instead.')
        args.command = 'collection'

    if args.command != 'collection':
        return

    if args.deps_file is None:
        args.deps_file = DEFAULT_FILE_BASE + f'{args.ansible_version}.deps'


def parse_args(program_name: str, args: List[str]) -> argparse.Namespace:
    """
    Parse and coerce the command line arguments.

    :arg program_name: The name of the program
    :arg args: A list of the command line arguments
    :returns: A :python:`argparse.Namespace`
    :raises InvalidArgumentError: Whenever there's something wrong with the arguments.
    """
    common_parser = get_common_parser()

    build_parser = argparse.ArgumentParser(add_help=False, parents=[common_parser])
    build_parser.add_argument('ansible_version', type=PypiVer,
                              help='The X.Y.Z version of Ansible that this will be for')
    build_parser.add_argument('--dest-dir', default='.',
                              help='Directory to write the output to')

    cache_parser = argparse.ArgumentParser(add_help=False)
    cache_parser.add_argument('--collection-cache', default=None,
                              help='Directory of cached collection tarballs.  Will be'
                              ' used if a collection tarball to be downloaded exists'
                              ' in here, and will be populated when downloading new'
                              ' tarballs.')

    build_step_parser = argparse.ArgumentParser(add_help=False)
    build_step_parser.add_argument('--build-file', default=None,
                                   help='File containing the list of collections with version'
                                   ' ranges. The default is to look for'
                                   ' $DEFAULT_FILE_BASE-X.Y.build inside of --dest-dir')
    build_step_parser.add_argument('--deps-file', default=None,
                                   help='File which will be written containing the list of'
                                   ' collections at versions which were included in this version'
                                   ' of Ansible. The default is to place'
                                   ' $BASENAME_OF_BUILD_FILE-X.Y.Z.deps into --dest-dir')

    parser = argparse.ArgumentParser(prog=program_name,
                                     description='Script to manage building Ansible')
    subparsers = parser.add_subparsers(title='Subcommands', dest='command',
                                       help='for help use antsibull-build SUBCOMMANDS -h')
    subparsers.required = True

    new_parser = subparsers.add_parser('new-ansible', parents=[build_parser],
                                       description='Generate a new build description from the'
                                       ' latest available versions of ansible-base and the'
                                       ' included collections')
    new_parser.add_argument('--pieces-file', default=None,
                            help='File containing a list of collections to include.  The'
                            f' default is to look for {DEFAULT_PIECES_FILE} inside of --dest-dir')
    new_parser.add_argument('--build-file', default=None,
                            help='File which will be written which contains the list'
                            ' of collections with version ranges.  The default is to'
                            ' place $BASENAME_OF_PIECES_FILE-X.Y.build into --dest-dir')

    build_single_parser = subparsers.add_parser('single',
                                                parents=[build_parser, cache_parser,
                                                         build_step_parser],
                                                description='Build a single-file Ansible')

    build_single_parser.add_argument('--debian', action='store_true',
                                     help='Include Debian/Ubuntu packaging files in'
                                     ' the resulting output directory')

    build_multiple_parser = subparsers.add_parser('multiple',
                                                  parents=[build_parser, cache_parser,
                                                           build_step_parser],
                                                  description='Build a multi-file Ansible')

    collection_parser = subparsers.add_parser('collection',
                                              parents=[build_parser],
                                              description='Build a collection which will'
                                              ' install Ansible')
    collection_parser.add_argument('--deps-file', default=None,
                                   help='File which contains the list of collections and'
                                   ' versions which were included in this version of Ansible'
                                   f' The default is to look for {DEFAULT_FILE_BASE}-X.Y.Z.deps'
                                   ' inside of --dest-dir')

    changelog_parser = subparsers.add_parser('changelog',
                                             parents=[build_parser, cache_parser],
                                             description='Build the Ansible changelog')
    changelog_parser.add_argument('--deps-dir', required=True,
                                  help='Directory which contains the versioning data')

    # Backwards compat.
    subparsers.add_parser('new-acd', add_help=False, parents=[new_parser])
    subparsers.add_parser('build-single', add_help=False, parents=[build_single_parser])
    subparsers.add_parser('build-multiple', add_help=False, parents=[build_multiple_parser])
    subparsers.add_parser('build-collection', add_help=False, parents=[collection_parser])

    args: argparse.Namespace = parser.parse_args(args)

    # Validation and coercion
    normalize_common_options(args)
    _normalize_build_options(args)
    _normalize_new_release_options(args)
    _normalize_release_build_options(args)
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
    if sys.version_info < (3, 8):
        print('Needs Python 3.8 or later')
        return 4

    return run(sys.argv)
