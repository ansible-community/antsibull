# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Parse documentation from ansible plugins using anible-doc."""

import typing as t

from .. import app_context
from ..logging import log
from .ansible_doc import get_ansible_plugin_info as ansible_doc_get_ansible_plugin_info
from .ansible_internal import get_ansible_plugin_info as ansible_internal_get_ansible_plugin_info
from . import AnsibleCollectionMetadata

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
    lib_ctx = app_context.lib_ctx.get()

    doc_parsing_backend = lib_ctx.doc_parsing_backend
    if doc_parsing_backend == 'ansible-internal':
        return await ansible_internal_get_ansible_plugin_info(
            venv, collection_dir, collection_names=collection_names)
    if doc_parsing_backend == 'ansible-doc':
        return await ansible_doc_get_ansible_plugin_info(
            venv, collection_dir, collection_names=collection_names)

    raise Exception('Invalid value for doc_parsing_backend: %s' % (doc_parsing_backend, ))
