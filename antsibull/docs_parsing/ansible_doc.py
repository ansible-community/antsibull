# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Parse documentation from ansible plugins using anible-doc."""

import asyncio
import json
import sys
import os
import traceback
import typing as t
from concurrent.futures import ThreadPoolExecutor

import sh

from .. import app_context
from ..compat import best_get_loop, create_task
from ..constants import DOCUMENTABLE_PLUGINS
from ..logging import log
from ..vendored.json_utils import _filter_non_json_lines
from .fqcn import get_fqcn_parts
from . import _get_environment, ParsingError, AnsibleCollectionMetadata

if t.TYPE_CHECKING:
    from ..venv import VenvRunner, FakeVenvRunner


mlog = log.fields(mod=__name__)


def _process_plugin_results(plugin_type: str,
                            plugin_names: t.Iterable[str],
                            plugin_info: t.Sequence[t.Union[sh.RunningCommand, Exception]]
                            ) -> t.Dict:
    """
    Process the results from running ansible-doc.

    In particular, log errors and remove them from the output.

    :arg plugin_type: The type of plugin.  See :attr:`DOCUMENTABLE_PLUGINS` for a list
        of allowed types.
    :arg plugin_names: Iterable of the plugin_names that were processed in the same order as the
        plugin_info.
    :arg plugin_info: List of results running sh.ansible_doc on each plugin.
    :returns: Dictionary mapping plugin_name to the results from ansible-doc.
    """
    flog = mlog.fields(func='_process_plugin_results')
    flog.debug('Enter')

    results = {}
    for plugin_name, ansible_doc_results in zip(plugin_names, plugin_info):
        plugin_log = flog.fields(plugin_type=plugin_type, plugin_name=plugin_name)

        if isinstance(ansible_doc_results, Exception):
            error_fields = {}
            error_fields['exception'] = traceback.format_exception(
                None, ansible_doc_results, ansible_doc_results.__traceback__)

            if isinstance(ansible_doc_results, sh.ErrorReturnCode):
                error_fields['stdout'] = ansible_doc_results.stdout.decode(
                    'utf-8', errors='surrogateescape')
                error_fields['stderr'] = ansible_doc_results.stderr.decode(
                    'utf-8', errors='surrogateescape')

            plugin_log.fields(**error_fields).error(
                'Exception while parsing documentation.  Will not document this plugin.')
            continue

        stdout = ansible_doc_results.stdout.decode('utf-8', errors='surrogateescape')

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

        try:
            ansible_doc_output = json.loads(_filter_non_json_lines(stdout)[0])
        except Exception as e:
            formatted_exception = traceback.format_exception(None, e, e.__traceback__)

            plugin_log.fields(ansible_doc_stdout=stdout, exception=formatted_exception,
                              traceback=traceback.format_exc()).error(
                                  'ansible-doc did not return json data.'
                                  ' Will not document this plugin.')
            continue

        results[fqcn] = ansible_doc_output[plugin_name]

    return results


async def _get_plugin_info(plugin_type: str, ansible_doc: 'sh.Command',
                           max_workers: int,
                           collection_names: t.Optional[t.List[str]] = None) -> t.Dict[str, t.Any]:
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
    :kwarg max_workers: The maximum number of threads that should be run in parallel by this
        function.
    :returns: Mapping of fqcn's to plugin_info.
    """
    flog = mlog.fields(func='_get_plugin_info')
    flog.debug('Enter')

    # Get the list of plugins
    ansible_doc_list_cmd_list = ['--list', '--t', plugin_type, '--json']
    if collection_names and len(collection_names) == 1:
        # Ansible-doc list allows to filter by one collection
        ansible_doc_list_cmd_list.append(collection_names[0])
    ansible_doc_list_cmd = ansible_doc(*ansible_doc_list_cmd_list)
    raw_plugin_list = ansible_doc_list_cmd.stdout.decode('utf-8', errors='surrogateescape')
    # Note: Keep ansible_doc_list_cmd around until we know if we need to use it in an error message.
    plugin_map = json.loads(_filter_non_json_lines(raw_plugin_list)[0])
    del raw_plugin_list
    del ansible_doc_list_cmd

    # Filter plugin map
    if collection_names is not None:
        prefixes = ['{name}.'.format(name=collection) for collection in collection_names]
        plugin_map = {
            key: value for key, value in plugin_map.items()
            if any(key.startswith(prefix) for prefix in prefixes)
        }

    loop = best_get_loop()

    # For each plugin, get its documentation
    extractors = {}
    executor = ThreadPoolExecutor(max_workers=max_workers)
    for plugin_name in plugin_map.keys():
        extractors[plugin_name] = loop.run_in_executor(executor, ansible_doc, '-t', plugin_type,
                                                       '--json', plugin_name)
    plugin_info = await asyncio.gather(*extractors.values(), return_exceptions=True)

    results = _process_plugin_results(plugin_type, extractors, plugin_info)

    flog.debug('Leave')
    return results


def get_collection_metadata(venv: t.Union['VenvRunner', 'FakeVenvRunner'],
                            env: t.Dict[str, str],
                            collection_names: t.Optional[t.List[str]] = None,
                            ) -> t.Dict[str, AnsibleCollectionMetadata]:
    collection_metadata = {}

    # Obtain ansible.builtin version
    if collection_names is None or 'ansible.builtin' in collection_names:
        venv_ansible = venv.get_command('ansible')
        ansible_version_cmd = venv_ansible('--version', _env=env)
        raw_result = ansible_version_cmd.stdout.decode('utf-8', errors='surrogateescape')
        path: t.Optional[str] = None
        version: t.Optional[str] = None
        for line in raw_result.splitlines():
            if line.strip().startswith('ansible python module location'):
                path = line.split('=', 2)[1].strip()
            if line.startswith('ansible '):
                version = line[len('ansible '):]
        collection_metadata['ansible.builtin'] = AnsibleCollectionMetadata(
            path=path, version=version)

    # Obtain collection versions
    venv_ansible_galaxy = venv.get_command('ansible-galaxy')
    ansible_collection_list_cmd = venv_ansible_galaxy('collection', 'list', _env=env)
    raw_result = ansible_collection_list_cmd.stdout.decode('utf-8', errors='surrogateescape')
    current_base_path = None
    for line in raw_result.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            if parts[0] == '#':
                current_base_path = parts[1]
            else:
                collection_name = parts[0]
                version = parts[1]
                if '.' in collection_name:
                    if collection_names is None or collection_name in collection_names:
                        namespace, name = collection_name.split('.', 2)
                        collection_metadata[collection_name] = AnsibleCollectionMetadata(
                            path=os.path.join(current_base_path, namespace, name),
                            version=None if version == '*' else version)

    return collection_metadata


async def get_ansible_plugin_info(venv: t.Union['VenvRunner', 'FakeVenvRunner'],
                                  collection_dir: t.Optional[str],
                                  collection_names: t.Optional[t.List[str]] = None
                                  ) -> t.Tuple[
                                      t.Mapping[str, t.Mapping[str, t.Any]],
                                      t.Mapping[str, AnsibleCollectionMetadata]]:
    """
    Retrieve information about all of the Ansible Plugins.

    :arg venv: A VenvRunner into which Ansible has been installed.
    :arg collection_dir: Directory in which the collections have been installed.
                         If ``None``, the collections are assumed to be in the current
                         search path for Ansible.
    :arg collection_names: Optional list of collections. If specified, will only collect
                           information for plugins in these collections.
    :returns: An tuple. The first component is a nested directory structure that looks like:

            plugin_type:
                plugin_name:  # Includes namespace and collection.
                    {information from ansible-doc --json.  See the ansible-doc documentation
                     for more info.}

        The second component is a Mapping of collection names to metadata.
    """
    flog = mlog.fields(func='get_ansible_plugin_info')
    flog.debug('Enter')

    env = _get_environment(collection_dir)

    # Setup an sh.Command to run ansible-doc from the venv with only the collections we
    # found as providers of extra plugins.

    venv_ansible_doc = venv.get_command('ansible-doc')
    venv_ansible_doc = venv_ansible_doc.bake('-vvv', _env=env)

    # We invoke _get_plugin_info once for each documentable plugin type.  Within _get_plugin_info,
    # new threads are spawned to handle waiting for ansible-doc to parse files and give us results.
    # To keep ourselves under thread_max, we need to divide the number of threads we're allowed over
    # each call of _get_plugin_info.
    # Why use thread_max instead of process_max?  Even though this ultimately invokes separate
    # ansible-doc processes, the limiting factor is IO as ansible-doc reads from disk.  So it makes
    # sense to scale up to thread_max instead of process_max.

    # Allocate more for modules because the vast majority of plugins are modules
    lib_ctx = app_context.lib_ctx.get()
    module_workers = max(int(.7 * lib_ctx.thread_max), 1)
    other_workers = int((lib_ctx.thread_max - module_workers) / (len(DOCUMENTABLE_PLUGINS) - 1))
    if other_workers < 1:
        other_workers = 1

    extractors = {}
    for plugin_type in DOCUMENTABLE_PLUGINS:
        if plugin_type == 'module':
            max_workers = module_workers
        else:
            max_workers = other_workers
        extractors[plugin_type] = create_task(
            _get_plugin_info(plugin_type, venv_ansible_doc, max_workers, collection_names))

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

    flog.debug('Retrieving collection metadata')
    collection_metadata = get_collection_metadata(venv, env, collection_names)

    flog.debug('Leave')
    return (plugin_map, collection_metadata)
