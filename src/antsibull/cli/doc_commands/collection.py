# Author: Toshio Kuratomi <tkuratom@redhat.com>
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Build documentation for one or more collections."""

from ... import app_context
from ...logging import log
from ...venv import FakeVenvRunner
from .stable import generate_docs_for_all_collections


mlog = log.fields(mod=__name__)


def generate_current_docs(indexes: bool, squash_hierarchy: bool) -> int:
    flog = mlog.fields(func='generate_current_docs')
    flog.debug('Begin processing docs')

    app_ctx = app_context.app_ctx.get()

    venv = FakeVenvRunner()

    return generate_docs_for_all_collections(
        venv, None, app_ctx.extra['dest_dir'], app_ctx.extra['collections'],
        create_indexes=indexes and not squash_hierarchy,
        squash_hierarchy=squash_hierarchy,
        breadcrumbs=app_ctx.breadcrumbs,
        use_html_blobs=app_ctx.use_html_blobs,
        fail_on_error=app_ctx.extra['fail_on_error'])


def generate_docs() -> int:
    """
    Create documentation for the current-collection subcommand.

    Current collection documentation creates documentation for one or multiple currently
    installed collections.

    :arg args: The parsed comand line args.
    :returns: A return code for the program.  See :func:`antsibull.cli.antsibull_docs.main` for
        details on what each code means.
    """
    app_ctx = app_context.app_ctx.get()

    indexes: bool = app_ctx.indexes
    squash_hierarchy: bool = app_ctx.extra['squash_hierarchy']

    if app_ctx.extra['use_current']:
        return generate_current_docs(indexes, squash_hierarchy)

    raise NotImplementedError('Priority to implement subcommands is stable, devel, plugin, and'
                              ' then collection commands. Only --use-current is implemented'
                              ' for the collection subcommand right now.')
