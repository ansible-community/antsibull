# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Argument parsing helpers."""

import argparse
import os.path


class InvalidArgumentError(Exception):
    """A problem parsing or validating a command line argument."""


def get_common_parser() -> argparse.ArgumentParser:
    """Return a parser with options common to all antsibull programs."""
    antsibull_parser = argparse.ArgumentParser(add_help=False)
    antsibull_parser.add_argument('--config-file', default=[], action='append',
                                  help='Specify one or more config files to use to configure the'
                                  ' program. If more than one are specified, keys from later'
                                  ' config files override keys from earlier ones.')

    return antsibull_parser


def normalize_common_options(args: argparse.Namespace) -> None:
    """
    Normalize and validate the common cli arguments.

    :arg args: The argparse parsed arguments.  The arguments added by the common parser will be
        validated and normalized.

    .. warning:: This function operates by side effect.

        Any normalization needed will be applied directly to ``args``.
    """
    for conf_file in args.config_file:
        if not os.path.isfile(args.config_file):
            raise InvalidArgumentError(f'The user specified config file, {args.config_file},'
                                       ' must exist.')
