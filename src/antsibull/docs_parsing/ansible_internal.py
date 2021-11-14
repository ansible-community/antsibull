# Author: Felix Fontein <felix@fontein.de>
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Parse documentation from ansible plugins using anible-doc."""

import json
import tempfile
import typing as t

from ..logging import log
from ..utils.get_pkg_data import get_antsibull_data
from ..vendored.json_utils import _filter_non_json_lines
from . import _get_environment, AnsibleCollectionMetadata

if t.TYPE_CHECKING:
    from ..venv import VenvRunner, FakeVenvRunner


mlog = log.fields(mod=__name__)


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

    venv_python = venv.get_command('python')

    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_file.write(get_antsibull_data('collection-enum.py'))
        collection_enum_args = [tmp_file.name]
        if collection_names is not None:
            # Script allows to filter by collections
            collection_enum_args.extend(collection_names)
        collection_enum_cmd = venv_python(*collection_enum_args, _env=env)
        raw_result = collection_enum_cmd.stdout.decode('utf-8', errors='surrogateescape')
        result = json.loads(_filter_non_json_lines(raw_result)[0])
        del raw_result
        del collection_enum_cmd

    plugin_map = {}
    for plugin_type, plugins in result['plugins'].items():
        plugin_map[plugin_type] = {}
        for plugin_name, plugin_data in plugins.items():
            if '.' not in plugin_name:
                plugin_name = 'ansible.builtin.{0}'.format(plugin_name)
            if 'ansible-doc' in plugin_data:
                plugin_map[plugin_type][plugin_name] = plugin_data['ansible-doc']
            else:
                plugin_log = flog.fields(plugin_type=plugin_type, plugin_name=plugin_name)
                plugin_log.fields(error=plugin_data['error']).error(
                    'Error while extracting documentation. Will not document this plugin.')

    collection_metadata = {}
    for collection_name, collection_data in result['collections'].items():
        collection_metadata[collection_name] = AnsibleCollectionMetadata(
            path=collection_data['path'],
            version=collection_data.get('version'))

    flog.debug('Leave')
    return (plugin_map, collection_metadata)
