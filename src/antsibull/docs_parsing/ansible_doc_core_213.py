# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2022
"""Parse documentation from ansible plugins using anible-doc from ansible-core 2.13+."""

import json
import typing as t

from ..constants import DOCUMENTABLE_PLUGINS
from ..logging import log
from ..vendored.json_utils import _filter_non_json_lines
from .ansible_doc import get_collection_metadata
from .fqcn import get_fqcn_parts
from . import _get_environment, AnsibleCollectionMetadata

if t.TYPE_CHECKING:
    from ..venv import VenvRunner, FakeVenvRunner  # pylint:disable=unused-import


mlog = log.fields(mod=__name__)


async def get_ansible_plugin_info(venv: t.Union['VenvRunner', 'FakeVenvRunner'],
                                  collection_dir: t.Optional[str],
                                  collection_names: t.Optional[t.List[str]] = None
                                  ) -> t.Tuple[
                                      t.Mapping[str, t.Mapping[str, t.Any]],
                                      t.Mapping[str, AnsibleCollectionMetadata]]:
    """
    Retrieve information about all of the Ansible Plugins. Requires ansible-core 2.13+.

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

    flog.debug('Retrieving plugin documentation')
    if collection_names and len(collection_names) == 1:
        # ansible-doc only allows *one* filter
        dump_metadata_cmd = venv_ansible_doc(
            '--metadata-dump', '--no-fail-on-errors', collection_names[0])
    else:
        dump_metadata_cmd = venv_ansible_doc('--metadata-dump', '--no-fail-on-errors')

    flog.debug('Loading plugin documentation')
    stdout = dump_metadata_cmd.stdout.decode('utf-8', errors='surrogateescape')
    ansible_doc_output = json.loads(_filter_non_json_lines(stdout)[0])

    flog.debug('Processing plugin documentation')
    plugin_map = {}
    for plugin_type in DOCUMENTABLE_PLUGINS:
        plugin_type_data = {}
        plugin_map[plugin_type] = plugin_type_data
        plugins_of_type = ansible_doc_output['all'].get(plugin_type, {})
        for plugin_name, plugin_data in plugins_of_type.items():
            # ansible-doc returns plugins shipped with ansible-core using no namespace and
            # collection.  For now, we fix these entries to use the ansible.builtin collection
            # here.  The reason we do it here instead of as part of a general normalization step
            # is that other plugins (site-specific ones from ANSIBLE_LIBRARY, for instance) will
            # also be returned with no collection name.  We know that we don't have any of those
            # in this code (because we set ANSIBLE_LIBRARY and other plugin path variables to
            # /dev/null) so we can safely fix this here but not outside the ansible-doc backend.
            fqcn = plugin_name
            try:
                namespace, collection, name = get_fqcn_parts(fqcn)
                collection = f'{namespace}.{collection}'

                # ansible-core devel branch will soon start to emit non-flattened FQCNs. This
                # needs to be handled better in antsibull-docs, but for now we modify the output
                # of --metadata-dump to conform to the output we had before (through
                # `ansible-doc --json` or the ansible-internal backend).
                # (https://github.com/ansible/ansible/pull/74963#issuecomment-1041580237)
                dot_position = name.rfind('.')
                if dot_position >= 0:
                    name = name[dot_position + 1:]
                fqcn = f'{collection}.{name}'
            except ValueError:
                name = plugin_name
                collection = 'ansible.builtin'
                fqcn = f'{collection}.{name}'

            # ansible-core devel branch will soon start to prepend _ to deprecated plugins when
            # --metadata-dump is used.
            # (https://github.com/ansible/ansible/pull/74963#issuecomment-1041580237)
            if collection == 'ansible.builtin' and fqcn.startswith('ansible.builtin._'):
                fqcn = fqcn.replace('_', '', 1)

            # Filter collection name
            if collection_names is not None and collection not in collection_names:
                flog.debug(f'Ignoring documenation for {plugin_type} plugin {fqcn}')
                continue

            plugin_type_data[fqcn] = plugin_data

    flog.debug('Retrieving collection metadata')
    collection_metadata = get_collection_metadata(venv, env, collection_names)

    flog.debug('Leave')
    return (plugin_map, collection_metadata)
