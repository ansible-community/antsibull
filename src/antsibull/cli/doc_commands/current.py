# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Entrypoint to the antsibull-docs script."""

from ... import app_context
from ...logging import log
from ...venv import FakeVenvRunner
from .stable import generate_docs_for_all_collections


mlog = log.fields(mod=__name__)


def generate_docs() -> int:
    """
    Create documentation for the current subcommand.

    Current documentation creates documentation for the currently installed version of Ansible,
    as well as the currently installed collections.

    :returns: A return code for the program.  See :func:`antsibull.cli.antsibull_docs.main` for
        details on what each code means.
    """
    flog = mlog.fields(func='generate_docs')
    flog.debug('Begin processing docs')

    app_ctx = app_context.app_ctx.get()

    venv = FakeVenvRunner()

    generate_docs_for_all_collections(
        venv, app_ctx.extra['collection_dir'], app_ctx.extra['dest_dir'],
        breadcrumbs=app_ctx.breadcrumbs)

    return 0
