# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Entrypoint to the antsibull-docs script."""

from ... import app_context
from ...compat import asyncio_run
from ...docs_parsing.ansible_doc import get_ansible_plugin_info
from ...logging import log
from ...venv import FakeVenvRunner
from ...write_docs import output_indexes, output_all_plugin_rst
from .stable import normalize_all_plugin_info, get_collection_contents


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

    # Get the list of plugins
    plugin_info = asyncio_run(get_ansible_plugin_info(venv, app_ctx.extra['collection_dir']))
    flog.debug('Finished parsing info from plugins')

    """
    # Turn these into some sort of decorator that will choose to dump or load the values
    # if a command line arg is specified.
    with open('dump_raw_plugin_info.json', 'w') as f:
        import json
        json.dump(plugin_info, f)
    flog.debug('Finished dumping raw plugin_info')
    """

    plugin_info, nonfatal_errors = asyncio_run(normalize_all_plugin_info(plugin_info))
    flog.debug('Finished normalizing data')
    # calculate_additional_info(plugin_info) (full_path)

    """
    with open('dump_normalized_plugin_info.json', 'w') as f:
        json.dump(plugin_info, f)
    flog.debug('Finished dumping normalized data')

    with open('dump_errors.json', 'w') as f:
        json.dump(nonfatal_errors, f)
    flog.debug('Finished dump errors')

    with open('dump_normalized_plugin_info.json', 'r') as f:
        import json
        plugin_info = json.load(f)
    flog.debug('Finished loading normalized data')

    with open('dump_errors.json', 'r') as f:
        from collections import defaultdict
        nonfatal_errors = json.load(f)
        nonfatal_errors = defaultdict(lambda: defaultdict(list), nonfatal_errors)
        for key, value in nonfatal_errors.items():
            nonfatal_errors[key] = defaultdict(list, value)
    flog.debug('Finished loading errors')
    """

    collection_info = get_collection_contents(plugin_info, nonfatal_errors)
    flog.debug('Finished writing collection data')

    asyncio_run(output_indexes(collection_info, app_ctx.extra['dest_dir']))
    flog.debug('Finished writing indexes')

    asyncio_run(output_all_plugin_rst(collection_info, plugin_info,
                                      nonfatal_errors, app_ctx.extra['dest_dir']))
    flog.debug('Finished writing plugin docs')

    return 0
