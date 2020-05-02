# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020


import argparse
import os.path
import sys

import packaging.version as pypiver

from ..new_acd import new_acd_command
from ..build_collection import build_collection_command
from ..build_acd_commands import build_single_command, build_multiple_command


DEFAULT_FILE_BASE = 'acd'
DEFAULT_PIECES_FILE = f'{DEFAULT_FILE_BASE}.in'

ARGS_MAP = {'new-acd': new_acd_command,
            'build-single': build_single_command,
            'build-multiple': build_multiple_command,
            'build-collection': build_collection_command,
            }


class InvalidArgumentError(Exception):
    pass


def parse_args(program_name, args):
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('acd_version', type=pypiver.Version,
                               help='The X.Y.Z version of ACD that this will be for')
    common_parser.add_argument('--dest-dir', default='.',
                               help='Directory to write the output to')

    build_parser = argparse.ArgumentParser(add_help=False)
    build_parser.add_argument('--build-file', default=None,
                              help='File containing the list of collections with version ranges')
    build_parser.add_argument('--deps-file', default=None,
                              help='File which will be written containing the list of collections'
                              ' at versions which were included in this version of ACD')

    parser = argparse.ArgumentParser(prog=program_name,
                                     description='Script to manage building ACD')
    subparsers = parser.add_subparsers(title='Subcommands', dest='command',
                                       help='for help use build-acd.py SUBCOMMANDS -h')

    new_parser = subparsers.add_parser('new-acd', parents=[common_parser],
                                       description='Generate a new build description from the'
                                       ' latest available versions of ansible-base and the'
                                       ' included collections')
    new_parser.add_argument('--pieces-file', default=None,
                            help='File containing a list of collections to include')
    new_parser.add_argument('--build-file', default=None,
                            help='File which will be written which contains the list'
                            ' of collections with version ranges')

    subparsers.add_parser('build-single',
                          parents=[common_parser, build_parser],
                          description='Build a single-file ACD')

    subparsers.add_parser('build-multiple',
                          parents=[common_parser, build_parser],
                          description='Build a multi-file ACD')

    collection_parser = subparsers.add_parser('build-collection',
                                              parents=[common_parser],
                                              description='Build a collection which will'
                                              ' install ACD')
    collection_parser.add_argument('--deps-file', default=None,
                                   help='File which contains the list of collections and'
                                   ' versions which were included in this version of ACD')

    args = parser.parse_args(args)

    #
    # Validation and coercion
    #

    #
    # Common options
    #
    if args.command is None:
        raise InvalidArgumentError('Please specify a subcommand to run')

    if not os.path.isdir(args.dest_dir):
        raise InvalidArgumentError(f'{args.dest_dir} must be an existing directory')

    #
    # New major release options
    #
    if args.command == 'new-acd':
        if args.pieces_file is not None:
            if not os.path.isfile(args.pieces_file):
                raise InvalidArgumentError(f'The pieces file, {args.pieces_file} must already'
                                           ' exist. It should contains one namespace.collection'
                                           ' per line')

        if args.build_file is None:
            basename = DEFAULT_FILE_BASE
            if args.pieces_file:
                basename = os.path.basename(os.path.splitext(args.pieces_file)[0])
            args.build_file = f'{basename}-{args.acd_version.major}.{args.acd_version.minor}.build'

    #
    # Release build options
    #
    if args.command in ('build-single', 'build-multiple'):
        if args.build_file is None:
            args.build_file = (DEFAULT_FILE_BASE
                               + f'-{args.acd_version.major}.{args.acd_version.minor}.build')

        if not os.path.isfile(args.build_file):
            raise InvalidArgumentError(f'The build file, {args.build_file} must already exist.'
                                       ' It should contains one namespace.collection per line')

        if args.deps_file is None:
            major_minor = f'-{args.acd_version.major}.{args.acd_version.minor}'
            basename = os.path.basename(os.path.splitext(args.build_file)[0])
            if basename.endswith(major_minor):
                basename = basename[:-len(major_minor)]

            args.deps_file = f'{basename}-{args.acd_version}.deps'

    #
    # Collection build options
    #
    if args.command == 'build-collection':
        if args.deps_file is None:
            args.deps_file = DEFAULT_FILE_BASE + f'{args.acd_version}.deps'

    return args


def run(args):
    program_name = os.path.basename(args[0])
    try:
        args = parse_args(program_name, args[1:])
    except InvalidArgumentError as e:
        print(e)
        return 2

    return ARGS_MAP[args.command](args)


def main():
    if sys.version_info < (3, 8):
        print('Needs Python 3.8 or later')
        sys.exit(1)

    return run(sys.argv)
