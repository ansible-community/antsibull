# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2022
"""Entrypoint to the antsibull-docs script."""

from ... import app_context
from ...collection_links import lint_collection_links
from ...lint_extra_docs import lint_collection_extra_docs_files
from ...logging import log


mlog = log.fields(mod=__name__)


def lint_collection_docs() -> int:
    """
    Lint collection documentation for inclusion into the collection's docsite.

    :returns: A return code for the program.  See :func:`antsibull.cli.antsibull_docs.main` for
        details on what each code means.
    """
    flog = mlog.fields(func='lint_collection_docs')
    flog.notice('Begin collection docs linting')

    app_ctx = app_context.app_ctx.get()

    collection_root = app_ctx.extra['collection_root_path']

    flog.notice('Linting extra docs files')
    errors = lint_collection_extra_docs_files(collection_root)

    flog.notice('Linting collection links')
    errors.extend(lint_collection_links(collection_root))

    messages = sorted(set(f'{error[0]}:{error[1]}:{error[2]}: {error[3]}' for error in errors))

    for message in messages:
        print(message)

    return 3 if messages else 0
