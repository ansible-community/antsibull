# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Entrypoint to the antsibull-docs script."""

import typing as t

from ...logging import log
from ...venv import FakeVenvRunner
from .stable import generate_docs_for_all_collections

if t.TYPE_CHECKING:
    import argparse


mlog = log.fields(mod=__name__)


def generate_docs(args: 'argparse.Namespace') -> int:
    """
    Create documentation for the current-collection subcommand.

    Current collection documentation creates documentation for one or multiple currently
    installed collections.

    :arg args: The parsed comand line args.
    :returns: A return code for the program.  See :func:`antsibull.cli.antsibull_docs.main` for
        details on what each code means.
    """
    flog = mlog.fields(func='generate_docs')
    flog.debug('Begin processing docs')

    venv = FakeVenvRunner()

    generate_docs_for_all_collections(
        venv, args.collection_dir, args.dest_dir, flog, args.collections)

    return 0
