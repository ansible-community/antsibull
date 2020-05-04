# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Output documentation."""

import asyncio
import os.path
import typing as t

import aiofiles
import asyncio_pool

from jinja2 import Template

from .constants import THREAD_MAX
from .docs_parsing.fqcn import get_fqcn_parts
from .jinja2.environment import doc_environment

#: Mapping of plugins to nonfatal errors.  This is the type to use when accepting the plugin.
#: The mapping is of plugin_type: plugin_name: [error_msgs]
PluginErrorsT = t.Mapping[str, t.Mapping[str, t.Sequence[str]]]


async def write_rst(plugin_name: str, plugin_type: str, plugin_record: t.Dict[str, t.Any],
                    nonfatal_errors: PluginErrorsT, plugin_tmpl: Template, error_tmpl: Template,
                    dest_dir: str) -> None:
    """
    Write the rst page for one plugin.

    :arg plugin_name: FQCN for the plugin.
    :arg plugin_type: The type of the plugin.  (module, inventory, etc)
    :arg plugin_record: The record for the plugin.  doc, examples, and return are the
        toplevel fields.
    :arg nonfatal_errors: Mapping of plugin to any nonfatal errors that will be displayed in place
        of some or all of the docs
    :arg plugin_tmpl: Template for the plugin.
    :arg error_tmpl: Template to use when there wasn't enough documentation for the plugin.
    :arg dest_dir: Destination directory for the plugin data.  For instance,
        :file:`ansible-checkout/docs/docsite/rst/`.  The directory structure underneath this
        directory will be created if needed.
    """
    namespace, collection, plugin_short_name = get_fqcn_parts(plugin_name)
    collection_name = '.'.join((namespace, collection))

    if not plugin_record:
        plugin_contents = error_tmpl.render(
            plugin_type=plugin_type, plugin_name=plugin_name,
            collection=collection_name,
            nonfatal_erros=nonfatal_errors)
    else:
        plugin_contents = plugin_tmpl.render(
            collection=collection_name,
            plugin_type=plugin_type,
            plugin_name=plugin_name,
            doc=plugin_record['doc'],
            examples=plugin_record['examples'],
            returndocs=plugin_record['return_'],
            nonfatal_errors=nonfatal_errors)

    collection_dir = os.path.join(dest_dir, 'collections', namespace, collection)
    # This is dangerous but the code that takes dest_dir from the user checks
    # permissions on it to make it as safe as possible.
    os.makedirs(collection_dir, exist_ok=True)

    plugin_file = os.path.join(collection_dir, f'{plugin_short_name}_{plugin_type}.rst')

    async with aiofiles.open(plugin_file, 'w') as f:
        await f.write(plugin_contents)


async def output_all_plugin_rst(plugin_info: t.Dict[str, t.Any],
                                nonfatal_errors: PluginErrorsT,
                                dest_dir: str) -> None:
    """
    Output rst files for each plugin.

    :arg plugin_info: Documentation information for all of the plugins.
    :arg nonfatal_errors: Mapping of plugins to nonfatal errors.  Using this to note on the docs
        pages when documentation wasn't formatted such that we could use it.
    :arg dest_dir: The directory to place the documentation in.
    """
    # Setup the jinja environment
    env = doc_environment(('antsibull.data', 'docsite'))
    # Get the templates
    plugin_tmpl = env.get_template('plugin.rst.j2')
    error_tmpl = env.get_template('plugin-error.rst.j2')

    writers = []
    async with asyncio_pool.AioPool(size=THREAD_MAX) as pool:
        for plugin_type, plugins_by_type in plugin_info.items():
            for plugin_name, plugin_record in plugins_by_type.items():
                writers.append(pool.spawn_n(write_rst(plugin_name, plugin_type, plugin_record,
                                                      nonfatal_errors[plugin_type][plugin_name],
                                                      plugin_tmpl, error_tmpl, dest_dir)))

        # Write docs for each plugin
        await asyncio.gather(*writers)


async def write_collection_list(collections: t.Iterable[str], template: Template,
                                dest_dir: str) -> None:
    """
    Write an index page listing all of the collections.

    Each collection will link to an index page listing all content in the collection.

    :arg collections: Iterable of all the collection names.
    :arg template: A template to render the collection index.
    :arg dest_dir: The destination directory to output the index into.
    """
    index_contents = template.render(collections=collections)
    index_file = os.path.join(dest_dir, 'index.rst')

    async with aiofiles.open(index_file, 'w') as f:
        await f.write(index_contents)


async def write_plugin_lists(collection_name: str,
                             plugin_maps: t.Mapping[str, t.Mapping[str, str]],
                             template: Template,
                             dest_dir: str) -> None:
    """
    Write an index page for each collection.

    The per-collection index page links to plugins for each collection.

    :arg plugin_maps: Mapping of plugin_type to Mapping of plugin_name to short_description.
    :arg template: A template to render the collection index.
    :arg dest_dir: The destination directory to output the index into.
    """
    index_contents = template.render(
        collection_name=collection_name,
        plugin_maps=plugin_maps)

    index_file = os.path.join(dest_dir, 'index.rst')

    async with aiofiles.open(index_file, 'w') as f:
        await f.write(index_contents)


async def output_indexes(collection_info: t.Mapping[str, t.Mapping[str, t.Mapping[str, str]]],
                         dest_dir: str) -> None:
    """
    Generate index pages for the collections.

    :arg collection_info: Mapping of collection_name to Mapping of plugin_type to Mapping of
        collection_name to short_description.
    :arg dest_dir: The directory to place the documentation in.
    """
    env = doc_environment(('antsibull.data', 'docsite'))
    # Get the templates
    collection_list_tmpl = env.get_template('list_of_collections.rst.j2')
    collection_plugins_tmpl = env.get_template('plugins_by_collection.rst.j2')

    writers = []
    async with asyncio_pool.AioPool(size=THREAD_MAX) as pool:
        collection_toplevel = os.path.join(dest_dir, 'collections')
        writers.append(pool.spawn_n(write_collection_list(collection_info.keys(),
                                                          collection_list_tmpl,
                                                          collection_toplevel)))

        for collection_name, plugin_maps in collection_info.items():
            collection_dir = os.path.join(collection_toplevel, *(collection_name.split('.')))
            writers.append(pool.spawn_n(write_plugin_lists(collection_name,
                                                           plugin_maps,
                                                           collection_plugins_tmpl,
                                                           collection_dir)))

        await asyncio.gather(*writers)
