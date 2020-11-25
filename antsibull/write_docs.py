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

from . import app_context
from .jinja2.environment import doc_environment
from .logging import log
from .docs_parsing import AnsibleCollectionMetadata


mlog = log.fields(mod=__name__)

#: Mapping of plugins to nonfatal errors.  This is the type to use when accepting the plugin.
#: The mapping is of plugin_type: plugin_name: [error_msgs]
PluginErrorsT = t.Mapping[str, t.Mapping[str, t.Sequence[str]]]

#: Mapping to collections to plugins.
#: The mapping is collection_name: plugin_type: plugin_name: plugin_short_description
CollectionInfoT = t.Mapping[str, t.Mapping[str, t.Mapping[str, str]]]

#: Plugins grouped first by plugin type, then by collection
#: The mapping is plugin_type: collection_name: plugin_name: plugin_short_description
PluginCollectionInfoT = t.Mapping[str, t.Mapping[str, t.Mapping[str, str]]]


async def write_rst(collection_name: str, collection_meta: AnsibleCollectionMetadata,
                    plugin_short_name: str, plugin_type: str,
                    plugin_record: t.Dict[str, t.Any], nonfatal_errors: t.Sequence[str],
                    plugin_tmpl: Template, error_tmpl: Template, dest_dir: str,
                    path_override: t.Optional[str] = None,
                    squash_hierarchy: bool = False) -> None:
    """
    Write the rst page for one plugin.

    :arg collection_name: Dotted colection name.
    :arg collection_meta: Collection metadata object.
    :arg plugin_short_name: short name for the plugin.
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
    :arg squash_hierarchy: If set to ``True``, no directory hierarchy will be used.
                           Undefined behavior if documentation for multiple collections are
                           created.
    """
    flog = mlog.fields(func='write_rst')
    flog.debug('Enter')

    namespace, collection = collection_name.split('.')
    plugin_name = '.'.join((collection_name, plugin_short_name))

    if not plugin_record:
        flog.fields(plugin_type=plugin_type,
                    plugin_name=plugin_name,
                    nonfatal_errors=nonfatal_errors
                    ).error('{plugin_name} did not return correct DOCUMENTATION.  An error page'
                            ' will be generated.', plugin_name=plugin_name)
        plugin_contents = error_tmpl.render(
            plugin_type=plugin_type, plugin_name=plugin_name,
            collection=collection_name,
            collection_version=collection_meta.version,
            nonfatal_errors=nonfatal_errors)
    else:
        if nonfatal_errors:
            flog.fields(plugin_type=plugin_type,
                        plugin_name=plugin_name,
                        nonfatal_errors=nonfatal_errors
                        ).error('{plugin_name} did not return correct RETURN or EXAMPLES.',
                                plugin_name=plugin_name)
        plugin_contents = plugin_tmpl.render(
            collection=collection_name,
            collection_version=collection_meta.version,
            plugin_type=plugin_type,
            plugin_name=plugin_name,
            doc=plugin_record['doc'],
            examples=plugin_record['examples'],
            returndocs=plugin_record['return'],
            nonfatal_errors=nonfatal_errors)

    if path_override is not None:
        plugin_file = path_override
    else:
        if squash_hierarchy:
            collection_dir = dest_dir
        else:
            collection_dir = os.path.join(dest_dir, 'collections', namespace, collection)
            # This is dangerous but the code that takes dest_dir from the user checks
            # permissions on it to make it as safe as possible.
            os.makedirs(collection_dir, mode=0o755, exist_ok=True)

        plugin_file = os.path.join(collection_dir, f'{plugin_short_name}_{plugin_type}.rst')

    async with aiofiles.open(plugin_file, 'w') as f:
        await f.write(plugin_contents)

    flog.debug('Leave')


async def output_all_plugin_rst(collection_to_plugin_info: CollectionInfoT,
                                plugin_info: t.Dict[str, t.Any],
                                nonfatal_errors: PluginErrorsT,
                                dest_dir: str,
                                collection_metadata: t.Mapping[str, AnsibleCollectionMetadata],
                                squash_hierarchy: bool = False) -> None:
    """
    Output rst files for each plugin.

    :arg collection_to_plugin_info: Mapping of collection_name to Mapping of plugin_type to Mapping
        of plugin_name to short_description.
    :arg plugin_info: Documentation information for all of the plugins.
    :arg nonfatal_errors: Mapping of plugins to nonfatal errors.  Using this to note on the docs
        pages when documentation wasn't formatted such that we could use it.
    :arg dest_dir: The directory to place the documentation in.
    :arg collection_metadata: Dictionary mapping collection names to collection metadata objects.
    :arg squash_hierarchy: If set to ``True``, no directory hierarchy will be used.
                           Undefined behavior if documentation for multiple collections are
                           created.
    """
    # Setup the jinja environment
    env = doc_environment(('antsibull.data', 'docsite'))
    # Get the templates
    plugin_tmpl = env.get_template('plugin.rst.j2')
    error_tmpl = env.get_template('plugin-error.rst.j2')

    writers = []
    lib_ctx = app_context.lib_ctx.get()
    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        for collection_name, plugins_by_type in collection_to_plugin_info.items():
            for plugin_type, plugins in plugins_by_type.items():
                for plugin_short_name, dummy_ in plugins.items():
                    plugin_name = '.'.join((collection_name, plugin_short_name))
                    writers.append(await pool.spawn(
                        write_rst(collection_name,
                                  collection_metadata[collection_name],
                                  plugin_short_name, plugin_type,
                                  plugin_info[plugin_type].get(plugin_name),
                                  nonfatal_errors[plugin_type][plugin_name], plugin_tmpl,
                                  error_tmpl, dest_dir, squash_hierarchy=squash_hierarchy)))

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


async def write_plugin_type_index(plugin_type: str,
                                  per_collection_plugins: t.Mapping[str, t.Mapping[str, str]],
                                  template: Template,
                                  dest_filename: str) -> None:
    """
    Write an index page for each plugin type.

    :arg plugin_type: The plugin type to write the index for.
    :arg per_collection_plugins: Mapping of collection_name to Mapping of plugin_name to
        short_description.
    :arg template: A template to render the plugin index.
    :arg dest_filename: The destination filename.
    """
    index_contents = template.render(
        plugin_type=plugin_type,
        per_collection_plugins=per_collection_plugins)

    async with aiofiles.open(dest_filename, 'w') as f:
        await f.write(index_contents)


async def write_plugin_lists(collection_name: str,
                             plugin_maps: t.Mapping[str, t.Mapping[str, str]],
                             template: Template,
                             dest_dir: str,
                             collection_meta: AnsibleCollectionMetadata) -> None:
    """
    Write an index page for each collection.

    The per-collection index page links to plugins for each collection.

    :arg plugin_maps: Mapping of plugin_type to Mapping of plugin_name to short_description.
    :arg template: A template to render the collection index.
    :arg dest_dir: The destination directory to output the index into.
    :arg collection_meta: Metadata for the collection.
    """
    index_contents = template.render(
        collection_name=collection_name,
        plugin_maps=plugin_maps,
        collection_version=collection_meta.version)

    # This is only safe because we made sure that the top of the directory tree we're writing to
    # (docs/docsite/rst) is only writable by us.
    os.makedirs(dest_dir, mode=0o755, exist_ok=True)
    index_file = os.path.join(dest_dir, 'index.rst')

    async with aiofiles.open(index_file, 'w') as f:
        await f.write(index_contents)


async def output_collection_index(collection_to_plugin_info: CollectionInfoT,
                                  dest_dir: str) -> None:
    """
    Generate top-level collection index page for the collections.

    :arg collection_to_plugin_info: Mapping of collection_name to Mapping of plugin_type to Mapping
        of plugin_name to short_description.
    :arg dest_dir: The directory to place the documentation in.
    """
    flog = mlog.fields(func='output_collection_index')
    flog.debug('Enter')

    env = doc_environment(('antsibull.data', 'docsite'))
    # Get the templates
    collection_list_tmpl = env.get_template('list_of_collections.rst.j2')

    collection_toplevel = os.path.join(dest_dir, 'collections')
    flog.fields(toplevel=collection_toplevel, exists=os.path.isdir(collection_toplevel)).debug(
        'collection_toplevel exists?')
    # This is only safe because we made sure that the top of the directory tree we're writing to
    # (docs/docsite/rst) is only writable by us.
    os.makedirs(collection_toplevel, mode=0o755, exist_ok=True)

    await write_collection_list(collection_to_plugin_info.keys(), collection_list_tmpl,
                                collection_toplevel)

    flog.debug('Leave')


async def output_plugin_indexes(plugin_info: PluginCollectionInfoT,
                                dest_dir: str) -> None:
    """
    Generate top-level plugin index pages for all plugins of a type in all collections.

    :arg plugin_info: Mapping of plugin_type to Mapping of collection_name to Mapping of
        plugin_name to short_description.
    :arg dest_dir: The directory to place the documentation in.
    """
    flog = mlog.fields(func='output_plugin_indexes')
    flog.debug('Enter')

    env = doc_environment(('antsibull.data', 'docsite'))
    # Get the templates
    plugin_list_tmpl = env.get_template('list_of_plugins.rst.j2')

    collection_toplevel = os.path.join(dest_dir, 'collections')
    flog.fields(toplevel=collection_toplevel, exists=os.path.isdir(collection_toplevel)).debug(
        'collection_toplevel exists?')
    # This is only safe because we made sure that the top of the directory tree we're writing to
    # (docs/docsite/rst) is only writable by us.
    os.makedirs(collection_toplevel, mode=0o755, exist_ok=True)

    writers = []
    lib_ctx = app_context.lib_ctx.get()
    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        for plugin_type, per_collection_data in plugin_info.items():
            filename = os.path.join(
                collection_toplevel, 'index_{type}.rst'.format(type=plugin_type))
            writers.append(await pool.spawn(
                write_plugin_type_index(
                    plugin_type, per_collection_data, plugin_list_tmpl, filename)))

        await asyncio.gather(*writers)

    flog.debug('Leave')


async def output_indexes(collection_to_plugin_info: CollectionInfoT,
                         dest_dir: str,
                         collection_metadata: t.Mapping[str, AnsibleCollectionMetadata],
                         squash_hierarchy: bool = False,
                         ) -> None:
    """
    Generate collection-level index pages for the collections.

    :arg collection_to_plugin_info: Mapping of collection_name to Mapping of plugin_type to Mapping
        of plugin_name to short_description.
    :arg dest_dir: The directory to place the documentation in.
    :arg collection_metadata: Dictionary mapping collection names to collection metadata objects.
    :arg squash_hierarchy: If set to ``True``, no directory hierarchy will be used.
                           Undefined behavior if documentation for multiple collections are
                           created.
    """
    flog = mlog.fields(func='output_indexes')
    flog.debug('Enter')

    if collection_metadata is None:
        collection_metadata = {}

    env = doc_environment(('antsibull.data', 'docsite'))
    # Get the templates
    collection_plugins_tmpl = env.get_template('plugins_by_collection.rst.j2')

    writers = []
    lib_ctx = app_context.lib_ctx.get()

    if not squash_hierarchy:
        collection_toplevel = os.path.join(dest_dir, 'collections')
        flog.fields(toplevel=collection_toplevel, exists=os.path.isdir(collection_toplevel)).debug(
            'collection_toplevel exists?')
        # This is only safe because we made sure that the top of the directory tree we're writing to
        # (docs/docsite/rst) is only writable by us.
        os.makedirs(collection_toplevel, mode=0o755, exist_ok=True)
    else:
        collection_toplevel = dest_dir

    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        for collection_name, plugin_maps in collection_to_plugin_info.items():
            if not squash_hierarchy:
                collection_dir = os.path.join(collection_toplevel, *(collection_name.split('.')))
            else:
                collection_dir = collection_toplevel
            writers.append(await pool.spawn(
                write_plugin_lists(collection_name, plugin_maps, collection_plugins_tmpl,
                                   collection_dir, collection_metadata[collection_name])))

        await asyncio.gather(*writers)

    flog.debug('Leave')
