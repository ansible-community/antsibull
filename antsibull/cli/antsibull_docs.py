# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Entrypoint to the antsibull-docs script."""

import argparse
import os.path
import stat
import sys
from typing import Callable, Dict, List

# import twiggy

# from ..config import load_config
from ..constants import DOCUMENTABLE_PLUGINS
from ..filesystem import writable_via_acls
from .doc_commands import collection, devel, plugin, stable

#: Mapping from command line subcommand names to functions which implement those
#: The functions need to take a single argument, the processed list of args.
ARGS_MAP: Dict[str, Callable] = {'devel': devel.generate_docs,
                                 'stable': stable.generate_docs,
                                 'collection': collection.generate_docs,
                                 'plugin': plugin.generate_docs,
                                 }

#: The filename for the file which lists raw collection names
DEFAULT_PIECES_FILE: str = 'acd.in'


class InvalidArgumentError(Exception):
    """A problem parsing or validating a command line argument."""


def _normalize_common_options(args: argparse.Namespace) -> None:
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

    if writable_via_acls(args.dest_dir, euid):
        raise InvalidArgumentError(f'Filesystem acls grant write on {args.dest_dir} to'
                                   ' additional users')


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
    # TODO: Need a function to return a parser with options that all antsibull
    # scripts use. Then we can add it as a parent to the common_parser.
    # antsibull_parser =

    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('--dest-dir', default='.',
                               help='Directory to write the output to')

    parser = argparse.ArgumentParser(prog=program_name,
                                     description='Script to manage generated documentation for'
                                     ' ansible')
    subparsers = parser.add_subparsers(title='Subcommands', dest='command',
                                       help='for help use  SUBCOMMANDS -h')

    # Document the next version of ansible
    devel_parser = subparsers.add_parser('devel', parents=[common_parser],
                                         description='Generate documentation for the next major'
                                         ' release of Ansible')
    devel_parser.add_argument('--pieces-file', default=DEFAULT_PIECES_FILE,
                              help='File containing a list of collections to include')

    stable_parser = subparsers.add_parser('stable',
                                          parents=[common_parser],
                                          description='Generate documentation for a current'
                                          ' version of ansible')
    stable_parser.add_argument('--deps-file', required=True,
                               help='File which contains the list of collections and'
                               ' versions which were included in this version of Ansible')

    collection_parser = subparsers.add_parser('collection',
                                              parents=[common_parser],
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
                                        parents=[common_parser],
                                        description='Generate documentation for a single plugin')
    file_parser.add_argument(nargs=1, dest='plugin', action='store',
                             choices=DOCUMENTABLE_PLUGINS,
                             help='A single file to document.')
    file_parser.add_argument('--plugin-type', action='store', default='module',
                             help='The type of the plugin')

    args: argparse.Namespace = parser.parse_args(args)

    # Validation and coercion
    _normalize_common_options(args)
    _normalize_devel_options(args)
    _normalize_stable_options(args)
    _normalize_plugin_options(args)

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
    program_name = os.path.basename(args[0])
    try:
        args: argparse.Namespace = parse_args(program_name, args[1:])
    except InvalidArgumentError as e:
        print(e)
        return 2

    # Need to finish implementing config loading
    # cfg = load_config(args.cfg_file)
    # if cfg['logging_cfg']:
    #    twiggy.dict_config(cfg['logging_cfg'])

    return ARGS_MAP[args.command](args)


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
