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
from ..args import InvalidArgumentError, get_toplevel_parser, normalize_toplevel_options
from ..config import load_config
from ..constants import DOCUMENTABLE_PLUGINS
from ..filesystem import UnableToCheck, writable_via_acls
from ..docs_parsing.fqcn import is_fqcn
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
DEFAULT_PIECES_FILE: str = 'ansible.in'


def _normalize_docs_options(args: argparse.Namespace) -> None:
    args.dest_dir = os.path.abspath(os.path.realpath(args.dest_dir))

    # We're going to be writing a deep hierarchy of files into this directory so we need to make
    # sure that the user understands that this needs to be a directory which has been secured
    # against malicious usage:

    # Exists already
    try:
        stat_results = os.stat(args.dest_dir)

        if not stat.S_ISDIR(stat_results.st_mode):
            raise FileNotFoundError()
    except FileNotFoundError:
        raise InvalidArgumentError(f'{args.dest_dir} must be an existing directory owned by you,'
                                   f' and only be writable by the owner')

    # Owned by the user
    euid = os.geteuid()
    if stat_results[stat.ST_UID] != euid:
        raise InvalidArgumentError(f'{args.dest_dir} must be owned by you, and only be writable'
                                   f' by the owner')

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


def _normalize_collection_options(args: argparse.Namespace) -> None:
    if args.command != 'collection':
        return

    if args.squash_hierarchy and len(args.collections) > 1:
        raise InvalidArgumentError('The option --squash-hierarchy can only be used when'
                                   ' only one collection is specified')


def _normalize_current_options(args: argparse.Namespace) -> None:
    if args.command != 'current':
        return

    if args.collection_dir is not None:
        if not os.path.isdir(os.path.join(args.collection_dir, 'ansible_collections')):
            raise InvalidArgumentError(f'The collection directory, {args.collection_dir}, must be'
                                       ' a directory containing a subdirectory ansible_collections')


def _normalize_plugin_options(args: argparse.Namespace) -> None:
    if args.command != 'plugin':
        return

    for plugin_name in args.plugin:
        if not is_fqcn(plugin_name) and not os.path.isfile(plugin_name):
            raise InvalidArgumentError(f'The plugin, {plugin_name}, must be an existing file,'
                                       f' or it must be a FQCN.')


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

    docs_parser = argparse.ArgumentParser(add_help=False)
    docs_parser.add_argument('--dest-dir', default='.',
                             help='Directory to write the output to')

    cache_parser = argparse.ArgumentParser(add_help=False)
    # TODO: Remove --ansible-base-cache once the ansible/ansible docs-build test is updated
    cache_parser.add_argument('--ansible-base-source', '--ansible-base-cache', default=None,
                              help='Checkout or expanded tarball of the ansible-base package.  If'
                              ' this is a git checkout it must be the HEAD of the branch you are'
                              ' building for. If it is an expanded tarball, the __version__ will'
                              ' be checked to make sure it is compatible with and the same or'
                              ' later version than requested by the deps file.')
    cache_parser.add_argument('--collection-cache', default=None,
                              help='Directory of collection tarballs.  These will be used instead'
                              ' of downloading fresh versions provided that they meet the criteria'
                              ' (Latest version of the collections known to galaxy).')

    parser = get_toplevel_parser(prog=program_name,
                                 description='Script to manage generated documentation for'
                                 ' ansible')
    subparsers = parser.add_subparsers(title='Subcommands', dest='command',
                                       help='for help use  SUBCOMMANDS -h')
    subparsers.required = True

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
    current_parser.add_argument('--collection-dir',
                                help='Path to the directory containing ansible_collections. If not'
                                ' specified, all collections in the currently configured ansible'
                                ' search paths will be used')

    collection_parser = subparsers.add_parser('collection',
                                              parents=[docs_parser],
                                              description='Generate documentation for a single'
                                              ' collection')
    collection_parser.add_argument('--collection-version', default='@latest',
                                   help='The version of the collection to document.  The special'
                                   ' version, "@latest" can be used to download and document the'
                                   ' latest version from galaxy.')
    collection_parser.add_argument('--use-current', action='store_true',
                                   help='Assumes that all arguments are collection names, and'
                                   ' these collections have been installed with the current'
                                   ' version of ansible. Specified --collection-version will be'
                                   ' ignored.')
    collection_parser.add_argument('--skip-indexes', action='store_true',
                                   help='Do not create the collection index and plugin indexes.'
                                   ' Automatically assumed when --squash-hierarchy is specified.')
    collection_parser.add_argument('--squash-hierarchy', action='store_true',
                                   help='Do not use the full hierarchy collections/namespace/name/'
                                   ' in the destination directory. Only valid if there is only'
                                   ' one collection specified.')
    collection_parser.add_argument(nargs='+', dest='collections',
                                   help='One or more collections to document.  If the names are'
                                   ' directories on disk, they will be parsed as expanded'
                                   ' collections. Otherwise, if they could be collection'
                                   ' names, they will be downloaded from galaxy.')

    file_parser = subparsers.add_parser('plugin',
                                        parents=[docs_parser],
                                        description='Generate documentation for a single plugin')
    file_parser.add_argument(nargs=1, dest='plugin', action='store',
                             help='A single file to document. Either a path to a file, or a FQCN.'
                             ' In the latter case, the plugin is assumed to be installed for'
                             ' the current ansible version.')
    file_parser.add_argument('--plugin-type', action='store', default='module',
                             choices=DOCUMENTABLE_PLUGINS,
                             help='The type of the plugin')

    flog.debug('Argument parser setup')

    if '--ansible-base-cache' in args:
        flog.warning('The CLI parameter, `--ansible-base-cache` has been renamed to'
                     ' `--ansible-base-source.  Please use that instead')

    args: argparse.Namespace = parser.parse_args(args)
    flog.fields(args=args).debug('Arguments parsed')

    # Validation and coercion
    normalize_toplevel_options(args)
    _normalize_docs_options(args)
    _normalize_devel_options(args)
    _normalize_stable_options(args)
    _normalize_current_options(args)
    _normalize_collection_options(args)
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
