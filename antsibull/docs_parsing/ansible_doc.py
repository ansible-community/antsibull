# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Parse documentation from ansible plugins using anible-doc."""

import asyncio
import json
import os
import sys
import traceback
from typing import TYPE_CHECKING, Any, Dict

import sh

from .fqcn import get_fqcn_parts
from ..compat import best_get_loop
from ..constants import DOCUMENTABLE_PLUGINS
from ..vendored.json_utils import _filter_non_json_lines

if TYPE_CHECKING:
    from ..venv import VenvRunner


#: Clear Ansible environment variables that set paths where plugins could be found.
ANSIBLE_PATH_ENVVARS: Dict[str, str] = {'ANSIBLE_COLLECTIONS_PATHS': "/dev/null",
                                        'ANSIBLE_ACTION_PLUGINS': "/dev/null",
                                        'ANSIBLE_CACHE_PLUGINS': "/dev/null",
                                        'ANSIBLE_CALLBACK_PLUGINS': "/dev/null",
                                        'ANSIBLE_CLICONF_PLUGINS': "/dev/null",
                                        'ANSIBLE_CONNECTION_PLUGINS': "/dev/null",
                                        'ANSIBLE_FILTER_PLUGINS': "/dev/null",
                                        'ANSIBLE_HTTPAPI_PLUGINS': "/dev/null",
                                        'ANSIBLE_INVENTORY_PLUGINS': "/dev/null",
                                        'ANSIBLE_LOOKUP_PLUGINS': "/dev/null",
                                        'ANSIBLE_LIBRARY': "/dev/null",
                                        'ANSIBLE_MODULE_UTILS': "/dev/null",
                                        'ANSIBLE_NETCONF_PLUGINS': "/dev/null",
                                        'ANSIBLE_ROLES_PATH': "/dev/null",
                                        'ANSIBLE_STRATEGY_PLUGINS': "/dev/null",
                                        'ANSIBLE_TERMINAL_PLUGINS': "/dev/null",
                                        'ANSIBLE_TEST_PLUGINS': "/dev/null",
                                        'ANSIBLE_VARS_PLUGINS': "/dev/null",
                                        'ANSIBLE_DOC_FRAGMENT_PLUGINS': "/dev/null",
                                        }


class ParsingError(Exception):
    """Error raised while parsing plugins for documentation."""


async def _get_plugin_info(plugin_type: str, ansible_doc: 'sh.Command') -> Dict[str, Any]:
    """
    Retrieve info about all Ansible plugins of a particular type.

    :arg plugin_type: The type of plugin.  See :attr:`DOCUMENTABLE_PLUGINS` for a list
        of allowed types.
    :arg ansible_doc: An :sh:obj:`sh.Command` object that will run the ansible-doc command.
        This command should already have been baked with any necessary environment and
        common arguments.
        :returns: A nested dictionary structure that looks like::
            Dictionary mapping to plugin information.  The dictionary looks like::

                plugin_name:  # This is the canonical name for the plugin and includes
                              # namespace.collection_name unless the plugin comes from
                              # ansible-base.
                    {information from ansible-doc --json.  See the ansible-doc documentation for
                     more info.}
    """
    # Get the list of plugins
    ansible_doc_list_cmd = ansible_doc('--list', '--t', plugin_type, '--json')
    raw_plugin_list = ansible_doc_list_cmd.stdout.decode('utf-8', errors='surrogateescape')
    # Note: Keep ansible_doc_list_cmd around until we know if we need to use it in an error message.
    plugin_map = json.loads(_filter_non_json_lines(raw_plugin_list)[0])
    del raw_plugin_list
    del ansible_doc_list_cmd

    loop = best_get_loop()

    # For each plugin, get its documentation
    extractors = {}
    for plugin_name in plugin_map.keys():
        extractors[plugin_name] = loop.run_in_executor(None, ansible_doc, '-t', plugin_type,
                                                       '--json', plugin_name)
    plugin_info = await asyncio.gather(*extractors.values(), return_exceptions=True)

    results = {}
    for plugin_name, ansible_doc_results in zip(extractors, plugin_info):
        err_msg = []
        stdout = ansible_doc_results.stdout.decode("utf-8", errors="surrogateescape")
        stderr = ansible_doc_results.stderr.decode("utf-8", errors="surrogateescape")

        if isinstance(ansible_doc_results, Exception):
            formatted_exception = traceback.format_exception(None, ansible_doc_results,
                                                             ansible_doc_results.__traceback__)
            err_msg.append(f'Exception while parsing documentation for {plugin_type} plugin:'
                           f' {plugin_name}.  Will not document this plugin.')
            err_msg.append(f'Exception:\n{"".join(formatted_exception)}')

        # Note: Exception will also be True.
        if isinstance(ansible_doc_results, sh.ErrorReturnCode):
            err_msg.append(f'Full process stdout:\n{stdout}')
            err_msg.append(f'Full process stderr:\n{stderr}')

        if err_msg:
            sys.stderr.write('\n'.join(err_msg))
            continue

        # ansible-doc returns plugins shipped with ansible-base using no namespace and collection.
        # For now, we fix these entries to use the ansible.builtin collection here.  The reason we
        # do it here instead of as part of a general normalization step is that other plugins
        # (site-specific ones from ANSIBLE_LIBRARY, for instance) will also be returned with no
        # collection name.  We know that we don't have any of those in this code (because we set
        # ANSIBLE_LIBRARY and other plugin path variables to /dev/null) so we can safely fix this
        # here but not outside the ansible-doc backend.
        fqcn = plugin_name
        try:
            get_fqcn_parts(fqcn)
        except ValueError:
            fqcn = f'ansible.builtin.{plugin_name}'

        results[fqcn] = json.loads(_filter_non_json_lines(stdout)[0])[plugin_name]

    return results


async def get_ansible_plugin_info(venv: 'VenvRunner',
                                  collection_dir: str) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve information about all of the Ansible Plugins.

    :arg venv: A VenvRunner into which Ansible has been installed.
    :arg collection_dir: Directory in which the collections have been installed.
    :returns: A nested directory structure that looks like::

        plugin_type:
            plugin_name:  # Includes namespace and collection.
                {information from ansible-doc --json.  See the ansible-doc documentation for more
                 info.}
    """
    # Setup an sh.Command to run ansible-doc from the venv with only the collections we
    # found as providers of extra plugins.
    env = os.environ.copy()
    env.update(ANSIBLE_PATH_ENVVARS)
    env['ANSIBLE_COLLECTIONS_PATHS'] = collection_dir

    venv_ansible_doc = venv.get_command('ansible-doc')
    venv_ansible_doc = venv_ansible_doc.bake('-vvv', _env=env)

    extractors = {}
    for plugin_type in DOCUMENTABLE_PLUGINS:
        extractors[plugin_type] = asyncio.create_task(
            _get_plugin_info(plugin_type, venv_ansible_doc))

    results = await asyncio.gather(*extractors.values(), return_exceptions=True)

    plugin_map = {}
    err_msg = []
    an_exception = None
    for plugin_type, extraction_result in zip(extractors, results):

        if isinstance(extraction_result, Exception):
            an_exception = extraction_result
            formatted_exception = traceback.format_exception(None, extraction_result,
                                                             extraction_result.__traceback__)
            err_msg.append(f'Exception while parsing documentation for {plugin_type} plugins')
            err_msg.append(f'Exception:\n{"".join(formatted_exception)}')

        # Note: Exception will also be True.
        if isinstance(extraction_result, sh.ErrorReturnCode):
            stdout = extraction_result.stdout.decode("utf-8", errors="surrogateescape")
            stderr = extraction_result.stderr.decode("utf-8", errors="surrogateescape")
            err_msg.append(f'Full process stdout:\n{stdout}')
            err_msg.append(f'Full process stderr:\n{stderr}')

        if err_msg:
            sys.stderr.write('\n'.join(err_msg))
            sys.stderr.write('\n')
            continue

        plugin_map[plugin_type] = extraction_result

    if an_exception:
        # We wanted to print out all of the exceptions raised by parsing the output but once we've
        # done so, we want to then fail by raising one of the exceptions.
        raise ParsingError('Parsing of plugins failed')

    return plugin_map
