# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2021
"""
Functions for parsing and interpreting collection metadata.
"""

import os
import typing as t

import asyncio
import asyncio_pool

from ansible.constants import DOCUMENTABLE_PLUGINS

from .. import app_context
from .. import yaml
from . import AnsibleCollectionMetadata


# A nested structure as follows:
#       plugin_type:
#           plugin_name:  # FQCN
#               tombstone: {tombstone record}
#               deprecation: {deprecation record}
#               redirect: str
CollectionRoutingT = t.Mapping[str, t.Mapping[str, t.Mapping[str, t.Any]]]


def add_symlinks(plugin_routing: t.Dict[str, t.Dict[str, t.Dict[str, t.Any]]],
                 collection_name: str,
                 collection_metadata: AnsibleCollectionMetadata
                 ) -> None:
    """
    Scans plugin folders for symbolic links, and updates plugin routing information accordingly.
    """
    if collection_name == 'ansible.builtin':
        # ansible-base/-core has a special directory structure we currently do not want
        # (or need) to handle
        return

    for plugin_type in DOCUMENTABLE_PLUGINS:
        directory_name = 'modules' if plugin_type == 'module' else plugin_type
        directory_path = os.path.join(collection_metadata.path, 'plugins', directory_name)
        plugin_type_routing = plugin_routing[plugin_type]
        if os.path.isdir(directory_path):
            for path, _, files in os.walk(directory_path):
                rel_path = os.path.relpath(path, directory_path)
                for file in files:
                    basename, ext = os.path.splitext(file)
                    if ext != '.py' and not (plugin_type == 'module' and ext == '.ps1'):
                        continue
                    file_path = os.path.join(path, file)
                    if os.path.islink(file_path):
                        src_components = os.path.normpath(
                            os.path.join(rel_path, basename)).split(os.sep)
                        dest_components = os.path.normpath(
                            os.path.join(
                                rel_path,
                                os.path.splitext(os.readlink(file_path))[0])).split(os.sep)
                        src_name = '.'.join(src_components)
                        src_fqcn = f'{collection_name}.{src_name}'
                        if src_fqcn not in plugin_type_routing:
                            plugin_type_routing[src_fqcn] = {}
                        if 'redirect' not in plugin_type_routing[src_fqcn]:
                            dst_name = '.'.join(dest_components)
                            dst_fqcn = f'{collection_name}.{dst_name}'
                            plugin_type_routing[src_fqcn]['redirect'] = dst_fqcn


async def load_collection_routing(collection_name: str,
                                  collection_metadata: AnsibleCollectionMetadata
                                  ) -> CollectionRoutingT:
    """
    Load plugin routing for a collection.
    """
    if collection_name == 'ansible.builtin':
        meta_runtime_path = os.path.join(
            collection_metadata.path, 'config', 'ansible_builtin_runtime.yml')
    else:
        meta_runtime_path = os.path.join(collection_metadata.path, 'meta', 'runtime.yml')

    if os.path.exists(meta_runtime_path):
        meta_runtime = yaml.load_yaml(meta_runtime_path)
    else:
        meta_runtime = {}

    plugin_routing_out: t.Dict[str, t.Dict[str, t.Dict[str, t.Any]]] = {}
    plugin_routing_in = meta_runtime.get('plugin_routing') or {}
    for plugin_type in DOCUMENTABLE_PLUGINS:
        plugin_type_id = 'modules' if plugin_type == 'module' else plugin_type
        plugin_type_routing = plugin_routing_in.get(plugin_type_id) or {}
        plugin_routing_out[plugin_type] = {
            f'{collection_name}.{plugin_name}': plugin_record
            for plugin_name, plugin_record in plugin_type_routing.items()
        }

    add_symlinks(plugin_routing_out, collection_name, collection_metadata)
    return plugin_routing_out


async def load_all_collection_routing(collection_metadata: t.Mapping[
                                          str, AnsibleCollectionMetadata]
                                      ) -> t.Dict[str, CollectionRoutingT]:
    requestors = {}

    lib_ctx = app_context.lib_ctx.get()
    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        for collection, metadata in collection_metadata.items():
            requestors[collection] = await pool.spawn(
                load_collection_routing(collection, metadata))

        responses = await asyncio.gather(*requestors.values())

    # Note: Python dicts have always had a stable order as long as you don't modify the dict.
    # So requestors (implicitly, the keys) and responses have a matching order here.
    return dict(zip(requestors, responses))
