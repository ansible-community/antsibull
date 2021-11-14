# Author: Toshio Kuratomi <tkuratom@redhat.com>
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

import json
import os
import traceback
import sys
import typing as t

import sh

from .stable import normalize_plugin_info
from ... import app_context
from ...augment_docs import augment_docs
from ...compat import asyncio_run
from ...docs_parsing import AnsibleCollectionMetadata
from ...docs_parsing.fqcn import get_fqcn_parts, is_fqcn
from ...jinja2.environment import doc_environment
from ...logging import log
from ...vendored.json_utils import _filter_non_json_lines
from ...venv import FakeVenvRunner
from ...write_docs import write_plugin_rst


mlog = log.fields(mod=__name__)


def generate_docs() -> int:
    """
    Create documentation for the current-plugin subcommand.

    Current plugin documentation creates documentation for one currently installed plugin.

    :returns: A return code for the program.  See :func:`antsibull.cli.antsibull_docs.main` for
        details on what each code means.
    """
    flog = mlog.fields(func='generate_docs')
    flog.debug('Begin processing docs')

    app_ctx = app_context.app_ctx.get()
    plugin_type: str = app_ctx.extra['plugin_type']
    plugin_name: str = app_ctx.extra['plugin'][0]

    if not is_fqcn(plugin_name):
        raise NotImplementedError('Priority to implement subcommands is stable, devel, plugin, and'
                                  ' then collection commands. Only the FQCN form is implemented'
                                  ' for the plugin subcommand right now.')

    output_path = os.path.join(app_ctx.extra['dest_dir'], f'{plugin_name}_{plugin_type}.rst')

    try:
        namespace, collection, plugin = get_fqcn_parts(plugin_name)
    except ValueError:
        namespace, collection = 'ansible', 'builtin'
        plugin = plugin_name
    plugin_name = '.'.join([namespace, collection, plugin])

    venv = FakeVenvRunner()
    venv_ansible_doc = venv.get_command('ansible-doc')
    venv_ansible_doc = venv_ansible_doc.bake('-vvv')
    try:
        ansible_doc_results = venv_ansible_doc('-t', plugin_type, '--json', plugin_name)
    except sh.ErrorReturnCode as exc:
        err_msg = []
        formatted_exception = traceback.format_exception(None, exc, exc.__traceback__)
        err_msg.append(f'Exception while parsing documentation for {plugin_type} plugin:'
                       f' {plugin_name}.  Will not document this plugin.')
        err_msg.append(f'Exception:\n{"".join(formatted_exception)}')

        stdout = exc.stdout.decode("utf-8", errors="surrogateescape")
        stderr = exc.stderr.decode("utf-8", errors="surrogateescape")

        err_msg.append(f'Full process stdout:\n{stdout}')
        err_msg.append(f'Full process stderr:\n{stderr}')

        sys.stderr.write('\n'.join(err_msg))
        return 1

    stdout = ansible_doc_results.stdout.decode("utf-8", errors="surrogateescape")

    plugin_info = json.loads(_filter_non_json_lines(stdout)[0])[plugin_name]
    flog.debug('Finished parsing info from plugin')

    plugin_info, errors = normalize_plugin_info(plugin_type, plugin_info)
    flog.debug('Finished normalizing data')

    # The cast is needed to make pyre happy. It seems to not being able to
    # understand that
    #     t.Dict[str, t.Dict[str, t.Dict[str, typing.Any]]]
    # is acceptable for
    #     t.MutableMapping[str, t.MutableMapping[str, typing.Any]].
    augment_docs(t.cast(t.MutableMapping[str, t.MutableMapping[str, t.Any]], {
        plugin_type: {
            plugin_name: plugin_info
        }
    }))

    # Setup the jinja environment
    env = doc_environment(('antsibull.data', 'docsite'))
    # Get the templates
    plugin_tmpl = env.get_template('plugin.rst.j2')
    error_tmpl = env.get_template('plugin-error.rst.j2')

    asyncio_run(write_plugin_rst(
        '.'.join([namespace, collection]), AnsibleCollectionMetadata.empty(), plugin, plugin_type,
        plugin_info, errors, plugin_tmpl, error_tmpl, '',
        path_override=output_path))
    flog.debug('Finished writing plugin docs')

    return 0
