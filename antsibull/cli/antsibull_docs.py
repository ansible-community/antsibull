# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Entrypoint to the antsibull-docs script."""

import argparse
import os
import os.path
import stat
import sys
from typing import Callable, Dict, List

import twiggy

from .. import app_context
from ..app_logging import log
from ..args import InvalidArgumentError, get_common_parser, normalize_common_options
from ..config import load_config
from ..constants import DOCUMENTABLE_PLUGINS
from ..filesystem import UnableToCheck, writable_via_acls
from .doc_commands import collection, current, devel, plugin, stable


mlog = log.fields(mod=__name__)

#: Mapping from command line subcommand names to functions which implement those
#: The functions need to take a single argument, the processed list of args.
ARGS_MAP: Dict[str, Callable] = {'devel': devel.generate_docs,
                                 'stable': stable.generate_docs,
                                 'current': current.generate_docs,
                                 'collection': collection.generate_docs,
                                 'plugin': plugin.generate_docs,
                                 }

#: The filename for the file which lists raw collection names
DEFAULT_PIECES_FILE: str = 'acd.in'


def _normalize_docs_options(args: argparse.Namespace) -> None:
    if args.command is None:
        raise InvalidArgumentError('Please specify a subcommand to run')

    args.dest_dir = os.path.expanduser(os.path.expandvars(args.dest_dir))
    args.dest_dir = os.path.abspath(os.path.realpath(args.dest_dir))

    # We're going to be writing a deep hierarchy of files into this directory so we need to make
    # sure that the user understands that this needs to be a directory which has been secured
    # against malicious usage:
    stat_results = os.stat(args.dest_dir)

    # Exists already
    if not stat.S_ISDIR(stat_results.st_mode):
        raise InvalidArgumentError(f'{args.dest_dir} must be an existing directory')

    # Owned by the user
    euid = os.geteuid()
    if stat_results[stat.ST_UID] != euid:
        raise InvalidArgumentError(f'{args.dest_dir} must be owned by you')

    # Writable only by the user
    if stat.S_IMODE(stat_results.st_mode) & (stat.S_IWOTH | stat.S_IWGRP):
        raise InvalidArgumentError(f'{args.dest_dir} must only be writable by the owner')

    try:
        if writable_via_acls(args.dest_dir, euid):
            raise InvalidArgumentError(f'Filesystem acls grant write on {args.dest_dir} to'
                                       ' additional users')
    except UnableToCheck:
        # We've done our best but some systems don't even have acls on their filesystem so we can't
        # error here.
        pass


def _normalize_devel_options(args: argparse.Namespace) -> None:
    if args.command != 'devel':
        return

    if not os.path.isfile(args.pieces_file):
        raise InvalidArgumentError(f'The pieces file, {args.pieces_file}, must already exist.'
                                   ' It should contain one namespace.collection per line')


def _normalize_stable_options(args: argparse.Namespace) -> None:
    if args.command != 'stable':
        return

    if not os.path.isfile(args.deps_file):
        raise InvalidArgumentError(f'The deps file, {args.deps_file}, must already exist.'
                                   ' It should contain one namespace.collection with version'
                                   ' per line')


def _normalize_current_options(args: argparse.Namespace) -> None:
    if args.command != 'current':
        return

    if not os.path.isdir(args.collection_dir) or not os.path.isdir(
            os.path.join(args.collection_dir, 'ansible_collections')):
        raise InvalidArgumentError(f'The collection directory, {args.collection_dir}, must be'
                                   ' a directory containing a subdirectory ansible_collections')


def _normalize_plugin_options(args: argparse.Namespace) -> None:
    if args.command != 'plugin':
        return

    if not os.path.isfile(args.plugin):
        raise InvalidArgumentError(f'The plugin file, {args.plugin}, must exist.')


def parse_args(program_name: str, args: List[str]) -> argparse.Namespace:
    """
    Parse and coerce the command line arguments.

    :arg program_name: The name of the program
    :arg args: A list of the command line arguments
    :returns: A :python:obj:`argparse.Namespace`
    :raises InvalidArgumentError: Whenever there's something wrong with the arguments.
    """
    flog = mlog.fields(func='parse_args')
    flog.fields(program_name=program_name, raw_args=args).info('Enter')

    common_parser = get_common_parser()

    docs_parser = argparse.ArgumentParser(add_help=False, parents=[common_parser])
    docs_parser.add_argument('--dest-dir', default='.',
                             help='Directory to write the output to')

    cache_parser = argparse.ArgumentParser(add_help=False)
    cache_parser.add_argument('--ansible-base-cache', default=None,
                              help='Checkout or expanded tarball of the ansible-base package.  If'
                              ' this is a git checkout it must be the HEAD of the cache branch.'
                              ' If it is an expanded tarball, the __version__ will be checked to'
                              ' make sure it is compatible with and the same or later version than'
                              ' requested by the depcs file.')
    cache_parser.add_argument('--collection-cache', default=None,
                              help='Directory of collection tarballs.  These will be used instead'
                              ' of downloading fresh versions provided that they meet the criteria'
                              ' (Latest version of the collections known to galaxy).')

    parser = argparse.ArgumentParser(prog=program_name,
                                     description='Script to manage generated documentation for'
                                     ' ansible')
    subparsers = parser.add_subparsers(title='Subcommands', dest='command',
                                       help='for help use  SUBCOMMANDS -h')

    # Document the next version of ansible
    devel_parser = subparsers.add_parser('devel', parents=[docs_parser, cache_parser],
                                         description='Generate documentation for the next major'
                                         ' release of Ansible')
    devel_parser.add_argument('--pieces-file', default=DEFAULT_PIECES_FILE,
                              help='File containing a list of collections to include')

    stable_parser = subparsers.add_parser('stable',
                                          parents=[docs_parser, cache_parser],
                                          description='Generate documentation for a current'
                                          ' version of ansible')
    stable_parser.add_argument('--deps-file', required=True,
                               help='File which contains the list of collections and'
                               ' versions which were included in this version of Ansible')

    current_parser = subparsers.add_parser('current',
                                           parents=[docs_parser],
                                           description='Generate documentation for the current'
                                           ' installed version of ansible and the current installed'
                                           ' collections')
    current_parser.add_argument('--collection-dir', required=True,
                                help='Path to the directory containing ansible_collections')

    collection_parser = subparsers.add_parser('collection',
                                              parents=[docs_parser],
                                              description='Generate documentation for a single'
                                              ' collection')
    collection_parser.add_argument('--collection-version', default='@latest',
                                   help='The version of the collection to document.  The special'
                                   ' version, "@latest" can be used to download and document the'
                                   ' latest version from galaxy')
    collection_parser.add_argument(nargs='+', dest='collections', action='append', default=[],
                                   help='One or more collections to document.  If the names are'
                                   ' directories on disk, they will be parsed as expanded'
                                   ' collections. Otherwise, if they could be collection'
                                   ' names, they will be downloaded from galaxy')

    file_parser = subparsers.add_parser('plugin',
                                        parents=[docs_parser],
                                        description='Generate documentation for a single plugin')
    file_parser.add_argument(nargs=1, dest='plugin', action='store',
                             choices=DOCUMENTABLE_PLUGINS,
                             help='A single file to document.')
    file_parser.add_argument('--plugin-type', action='store', default='module',
                             help='The type of the plugin')

    flog.debug('Argument parser setup')

    args: argparse.Namespace = parser.parse_args(args)
    flog.fields(args=args).debug('Arguments parsed')

    # Validation and coercion
    normalize_common_options(args)
    _normalize_docs_options(args)
    _normalize_devel_options(args)
    _normalize_stable_options(args)
    _normalize_current_options(args)
    _normalize_plugin_options(args)
    flog.fields(args=args).debug('Arguments normalized')

    # Note: collections aren't validated as existing files or collection names here because talking
    # to galaxy to validate the collection names goes beyond the scope of what parsing and
    # validating the command line should do.

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
    flog.fields(args=args).info('Arguments parsed')

    cfg = load_config(args.config_file)
    flog.fields(config=cfg).info('Config loaded')

    context_data = app_context.create_contexts(args=args, cfg=cfg)
    with app_context.app_and_lib_context(context_data) as (app_ctx, dummy_):
        twiggy.dict_config(app_ctx.logging_cfg.dict())
        flog.debug('Set logging config')

        flog.fields(command=args.command).info('Action')
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
        :3: Unexpected problem downloading ansible-base
    """
    return run(sys.argv)
