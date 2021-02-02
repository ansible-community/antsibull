# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2021
"""
Functions for parsing and interpreting collection metadata.
"""

from collections import defaultdict

import datetime
import os
import typing as t

import asyncio
import asyncio_pool

from ansible.constants import DOCUMENTABLE_PLUGINS

from .. import app_context
from .. import yaml
from . import AnsibleCollectionMetadata
from .fqcn import get_fqcn_parts


# A nested structure as follows:
#       plugin_type:
#           plugin_name:  # FQCN
#               tombstone: t.Optional[{tombstone record}]
#               deprecation: t.Optional[{deprecation record}]
#               redirect: t.Optional[str]
#               redirect_is_symlink: t.Optional[bool]
CollectionRoutingT = t.Mapping[str, t.Mapping[str, t.Mapping[str, t.Any]]]


COLLECTIONS_WITH_FLATMAPPING = (
    'community.general',
    'community.network',
)


def add_symlink(collection_name: str, src_components: t.List[str], dest_components: t.List[str],
                plugin_type_routing: t.Dict[str, t.Dict[str, t.Any]]) -> None:
    """
    Add symlink redirect for a single plugin.
    """
    # Compose source FQCN
    src_name = '.'.join(src_components)
    src_fqcn = f'{collection_name}.{src_name}'
    if src_fqcn not in plugin_type_routing:
        plugin_type_routing[src_fqcn] = {}
    # Compose destination FQCN
    dst_name = '.'.join(dest_components)
    dst_fqcn = f'{collection_name}.{dst_name}'
    if 'redirect' not in plugin_type_routing[src_fqcn]:
        plugin_type_routing[src_fqcn]['redirect'] = dst_fqcn
    if plugin_type_routing[src_fqcn]['redirect'] == dst_fqcn:
        plugin_type_routing[src_fqcn]['redirect_is_symlink'] = True


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
                        add_symlink(
                            collection_name, src_components, dest_components, plugin_type_routing)


def process_dates(plugin_record: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
    for tlkey in ('tombstone', 'deprecation'):
        if tlkey in plugin_record and 'removal_date' in plugin_record[tlkey]:
            date = plugin_record[tlkey]['removal_date']
            if isinstance(date, datetime.datetime):
                date = date.date()
            if isinstance(date, datetime.date):
                date = date.isoformat()
            plugin_record[tlkey]['removal_date'] = date
    return plugin_record


def find_flatmapping_short_long_maps(plugin_routing_type: t.Dict[str, t.Dict[str, t.Any]],
                                     ) -> t.Tuple[t.Mapping[str, str],
                                                  t.Mapping[str, t.Tuple[str, bool]]]:
    """
    Collect all short and long names, and mappings between them.

    Short names are FQCN like community.general.rax_facts, and long names are FQCN like
    community.general.cloud.rackspace.rax_facts.

    Returns two tuples. The first element maps short names to long names. The second element
    maps long names to pairs (short name, is symbolic link).
    """
    shortname_to_longname: t.Dict[str, str] = {}
    longname_to_shortname: t.Dict[str, t.Tuple[str, bool]] = {}
    for plugin_name, routing_data in plugin_routing_type.items():
        coll_ns, coll_name, plug_name = get_fqcn_parts(plugin_name)
        if 'tombstone' not in routing_data and 'redirect' in routing_data:
            redirect = routing_data['redirect']
            redir_coll_ns, redir_coll_name, redir_plug_name = get_fqcn_parts(redirect)
            if coll_ns == redir_coll_ns and coll_name == redir_coll_name:
                if '.' not in plug_name and redir_plug_name.endswith(f'.{plug_name}'):
                    is_symlink = routing_data.get('redirect_is_symlink') or False
                    shortname_to_longname[plugin_name] = redirect
                    longname_to_shortname[redirect] = (plugin_name, is_symlink)
                elif '.' in plug_name:
                    # Sometimes plugins/modules/foo_facts.py could be a link to
                    # plugins/modules/subdir1/subdir2/foo_info.py, and
                    # plugins/modules/subdir1/subdir2/foo_facts.py also links to the same
                    # _info module. In that case, artificially construct the shortname
                    # <-> longname mapping
                    _, short_name = plug_name.rsplit('.', 1)
                    short_fqcn = f'{coll_ns}.{coll_name}.{short_name}'
                    if plugin_routing_type.get(short_fqcn, {}).get('redirect') == redirect:
                        shortname_to_longname[short_fqcn] = plugin_name
                        longname_to_shortname[plugin_name] = (short_fqcn, False)
    return shortname_to_longname, longname_to_shortname


def remove_flatmapping_artefacts(plugin_routing: t.Dict[str, t.Dict[str, t.Dict[str, t.Any]]]
                                 ) -> None:
    """
    For collections which use flatmapping (like community.general and community.network),
    there will be several redirects which look confusing, like the community.general.rax_facts
    module redirects to community.general.cloud.rackspace.rax_facts, which in turn redirects to
    community.general.cloud.rackspace.rax_info. Such redirects are condensed by this function
    into one redirect from community.general.rax_facts to community.general.rax_info.
    """
    for plugin_type, plugin_routing_type in plugin_routing.items():
        # First collect all short and long names.
        shortname_to_longname, longname_to_shortname = find_flatmapping_short_long_maps(
            plugin_routing_type)
        # Now shorten redirects
        for plugin_name, routing_data in list(plugin_routing_type.items()):
            if 'redirect' in routing_data:
                redirect = routing_data['redirect']
                if shortname_to_longname.get(plugin_name) == redirect:
                    routing_data.pop('redirect')
                    routing_data.pop('redirect_is_symlink', None)
                    if 'deprecation' not in routing_data and 'tombstone' not in routing_data:
                        plugin_routing_type.pop(plugin_name, None)
                elif redirect in longname_to_shortname:
                    routing_data['redirect'], is_symlink = longname_to_shortname[redirect]
                    if routing_data.get('redirect_is_symlink') and not is_symlink:
                        routing_data.pop('redirect_is_symlink')
                if plugin_name in longname_to_shortname:
                    if 'tombstone' not in routing_data and 'deprecation' not in routing_data:
                        plugin_routing_type.pop(plugin_name, None)


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
            f'{collection_name}.{plugin_name}': process_dates(plugin_record)
            for plugin_name, plugin_record in plugin_type_routing.items()
        }

    add_symlinks(plugin_routing_out, collection_name, collection_metadata)
    if collection_name in COLLECTIONS_WITH_FLATMAPPING:
        remove_flatmapping_artefacts(plugin_routing_out)
    return plugin_routing_out


async def load_all_collection_routing(collection_metadata: t.Mapping[
                                          str, AnsibleCollectionMetadata]
                                      ) -> CollectionRoutingT:
    # Collection
    lib_ctx = app_context.lib_ctx.get()
    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        requestors = []
        for collection, metadata in collection_metadata.items():
            requestors.append(await pool.spawn(
                load_collection_routing(collection, metadata)))

        responses = await asyncio.gather(*requestors)

    # Merge per-collection routing into one big routing table
    global_plugin_routing: t.Dict[str, t.Dict[str, t.Dict[str, t.Any]]] = {}
    for plugin_type in DOCUMENTABLE_PLUGINS:
        global_plugin_routing[plugin_type] = {}
        for collection_plugin_routing in responses:
            global_plugin_routing[plugin_type].update(collection_plugin_routing[plugin_type])

    return global_plugin_routing


def compare_all_but(dict_a, dict_b, *keys_to_ignore):
    """
    Compare two dictionaries
    """
    sentinel = object()
    for key, value in dict_a.items():
        if key in keys_to_ignore:
            continue
        if value != dict_b.get(key, sentinel):
            return False
    for key, value in dict_b.items():
        if key in keys_to_ignore:
            continue
        if value != dict_a.get(key, sentinel):
            return False
    return True


def remove_redirect_duplicates(plugin_info: t.MutableMapping[str, t.MutableMapping[str, t.Any]],
                               collection_routing: CollectionRoutingT) -> None:
    """
    Remove duplicate plugin docs that come from symlinks (or once ansible-docs supports them,
    other plugin routing redirects).
    """
    for plugin_type, plugin_map in plugin_info.items():
        plugin_routing = collection_routing[plugin_type]
        for plugin_name, plugin_record in list(plugin_map.items()):
            # Check redirect
            if plugin_name in plugin_routing and 'redirect' in plugin_routing[plugin_name]:
                destination = plugin_routing[plugin_name]['redirect']
                if destination in plugin_map and destination != plugin_name:
                    # Heuristic: if we have a redirect, and docs for both this plugin and the
                    # redireted one are generated from the same plugin filename, then we can
                    # remove this plugin's docs and generate a redirect stub instead.
                    if compare_all_but(
                            plugin_record['doc'], plugin_map[destination]['doc'], 'filename'):
                        del plugin_map[plugin_name]


def find_stubs(plugin_info: t.MutableMapping[str, t.MutableMapping[str, t.Any]],
               collection_routing: CollectionRoutingT
               ) -> t.Mapping[str, t.Mapping[str, t.Mapping[str, t.Any]]]:
    """
    Find plugin stubs to write. Returns a nested structure:

        collection:
            plugin_type:
                plugin_short_name:
                    tombstone: t.Optional[{tombstone record}]
                    deprecation: t.Optional[{deprecation record}]
                    redirect: t.Optional[str]
                    redirect_is_symlink: t.Optional[bool]
    """
    stubs_info: t.DefaultDict[str, t.DefaultDict[str, t.Dict[str, t.Any]]] = (
        defaultdict(lambda: defaultdict(dict))
    )
    for plugin_type, plugin_routing in collection_routing.items():
        plugin_info_type = plugin_info.get(plugin_type) or {}
        for plugin_name, plugin_data in plugin_routing.items():
            if 'tombstone' not in plugin_data and 'redirect' not in plugin_data:
                # Ignore pure deprecations
                continue
            if plugin_name not in plugin_info_type:
                coll_ns, coll_name, plug_name = get_fqcn_parts(plugin_name)
                stubs_info[f'{coll_ns}.{coll_name}'][plugin_type][plug_name] = plugin_data
    return stubs_info
