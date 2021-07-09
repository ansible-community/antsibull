# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Entrypoint to the antsibull-docs script."""

import asyncio
import os
import os.path
import tempfile
import typing as t
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import aiohttp
import asyncio_pool
from pydantic import ValidationError

from ... import app_context
from ...ansible_base import get_ansible_base
from ...augment_docs import augment_docs
from ...collections import install_together
from ...compat import asyncio_run, best_get_loop
from ...dependency_files import DepsFile
from ...extra_docs import load_collections_extra_docs
from ...docs_parsing.parsing import get_ansible_plugin_info
from ...docs_parsing.fqcn import get_fqcn_parts
from ...docs_parsing.routing import (
    find_stubs,
    load_all_collection_routing,
    remove_redirect_duplicates,
)
from ...galaxy import CollectionDownloader
from ...logging import log
from ...schemas.docs import DOCS_SCHEMAS
from ...venv import VenvRunner, FakeVenvRunner
from ...write_docs import (
    output_all_plugin_rst,
    output_all_plugin_stub_rst,
    output_collection_index,
    output_collection_namespace_indexes,
    output_indexes,
    output_plugin_indexes,
    output_extra_docs,
)
from ...utils.transformations import get_collection_namespaces

if t.TYPE_CHECKING:
    import semantic_version as semver


mlog = log.fields(mod=__name__)

#: Mapping of plugins to nonfatal errors.  This is the type to use when returning the mapping.
PluginErrorsRT = t.DefaultDict[str, t.DefaultDict[str, t.List[str]]]


async def retrieve(ansible_base_version: str,
                   collections: t.Mapping[str, str],
                   tmp_dir: str,
                   galaxy_server: str,
                   ansible_base_source: t.Optional[str] = None,
                   collection_cache: t.Optional[str] = None) -> t.Dict[str, 'semver.Version']:
    """
    Download ansible-core and the collections.

    :arg ansible_base_version: Version of ansible-base/-core to download.
    :arg collections: Map of collection names to collection versions to download.
    :arg tmp_dir: The directory to download into.
    :arg galaxy_server: URL to the galaxy server.
    :kwarg ansible_base_source: If given, a path to an ansible-core checkout or expanded sdist.
        This will be used instead of downloading an ansible-core package if the version matches
        with ``ansible_base_version``.
    :kwarg collection_cache: If given, a path to a directory containing collection tarballs.
        These tarballs will be used instead of downloading new tarballs provided that the
        versions match the criteria (latest compatible version known to galaxy).
    :returns: Map of collection name to directory it is in.  ansible-core will
        use the special key, `_ansible_base`.
    """
    collection_dir = os.path.join(tmp_dir, 'collections')
    os.mkdir(collection_dir, mode=0o700)

    requestors = {}

    lib_ctx = app_context.lib_ctx.get()
    async with aiohttp.ClientSession() as aio_session:
        async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
            requestors['_ansible_base'] = await pool.spawn(
                get_ansible_base(aio_session, ansible_base_version, tmp_dir,
                                 ansible_base_source=ansible_base_source))

            downloader = CollectionDownloader(aio_session, collection_dir,
                                              galaxy_server=galaxy_server,
                                              collection_cache=collection_cache)
            for collection, version in collections.items():
                requestors[collection] = await pool.spawn(
                    downloader.download(collection, version))

            responses = await asyncio.gather(*requestors.values())

    # Note: Python dicts have always had a stable order as long as you don't modify the dict.
    # So requestors (implicitly, the keys) and responses have a matching order here.
    return dict(zip(requestors, responses))


def normalize_plugin_info(plugin_type: str,
                          plugin_info: t.Mapping[str, t.Any]
                          ) -> t.Tuple[t.Dict[str, t.Any], t.List[str]]:
    """
    Normalize and validate all of the plugin docs.

    :arg plugin_type: The type of plugins that we're getting docs for.
    :arg plugin_info: Mapping of plugin_info.  The toplevel keys are plugin names.
        See the schema in :mod:`antsibull.schemas.docs` for what the data should look like and just
        how much conversion we can perform on it.
    :returns: A tuple containing a "copy" of plugin_info with all of the data normalized and a list
        of nonfatal errors.  The plugin_info dict will follow the structure expressed in the schemas
        in :mod:`antsibull.schemas.docs`.  The nonfatal errors are strings representing the problems
        encountered.
    """
    new_info = {}
    errors = []
    # Note: loop through "doc" before any other keys.
    for field in ('doc', 'examples', 'return'):
        try:
            field_model = DOCS_SCHEMAS[plugin_type][field].parse_obj({field: plugin_info[field]})
        except ValidationError as e:
            if field == 'doc':
                # We can't recover if there's not a doc field
                # pydantic exceptions are not picklable (probably due to bugs in the pickle module)
                # so convert it to an exception type which is picklable
                raise ValueError(str(e))

            # But we can use the default value (some variant of "empty") for everything else
            # Note: We looped through doc first and returned an exception if doc did not normalize
            # so we're able to use it in the error message here.
            errors.append(f'Unable to normalize {new_info["doc"]["name"]}: {field}'
                          f' due to: {str(e)}')

            field_model = DOCS_SCHEMAS[plugin_type][field].parse_obj({})

        new_info.update(field_model.dict(by_alias=True))

    return (new_info, errors)


async def normalize_all_plugin_info(plugin_info: t.Mapping[str, t.Mapping[str, t.Any]]
                                    ) -> t.Tuple[t.Dict[str, t.Dict[str, t.Any]], PluginErrorsRT]:
    """
    Normalize the data in plugin_info so that it is ready to be passed to the templates.

    :arg plugin_info: Mapping of information about plugins.  This contains information about all of
        the plugins that are to be documented. See the schema in :mod:`antsibull.schemas.docs` for
        the structure of the information.
    :returns: A tuple of plugin_info (this is a "copy" of the input plugin_info with all of the
        data normalized) and a mapping of errors.  The plugin_info may have less records than the
        input plugin_info if there were plugin records which failed to validate.  The mapping of
        errors takes the form of:

        .. code-block:: yaml

            plugin_type:
                plugin_name:
                    - error string
                    - error string
    """
    loop = best_get_loop()
    lib_ctx = app_context.lib_ctx.get()
    executor = ProcessPoolExecutor(max_workers=lib_ctx.process_max)

    # Normalize each plugin in a subprocess since normalization is CPU bound
    normalizers = {}
    for plugin_type, plugin_list_for_type in plugin_info.items():
        for plugin_name, plugin_record in plugin_list_for_type.items():
            normalizers[(plugin_type, plugin_name)] = loop.run_in_executor(
                executor, normalize_plugin_info, plugin_type, plugin_record)

    results = await asyncio.gather(*normalizers.values(), return_exceptions=True)

    new_plugin_info = defaultdict(dict)
    nonfatal_errors = defaultdict(lambda: defaultdict(list))
    for (plugin_type, plugin_name), plugin_record in zip(normalizers, results):
        # Errors which broke doc parsing (and therefore we won't have enough info to
        # build a docs page)
        if isinstance(plugin_record, Exception):
            # An exception means there is no usable documentation for this plugin
            # Record a nonfatal error and then move on
            nonfatal_errors[plugin_type][plugin_name].append(str(plugin_record))
            continue

        # Errors where we have at least docs.  We can still create a docs page for these with some
        # information left out
        if plugin_record[1]:
            nonfatal_errors[plugin_type][plugin_name].extend(plugin_record[1])

        new_plugin_info[plugin_type][plugin_name] = plugin_record[0]

    return new_plugin_info, nonfatal_errors


def get_plugin_contents(plugin_info: t.Mapping[str, t.Mapping[str, t.Any]],
                        nonfatal_errors: PluginErrorsRT
                        ) -> t.DefaultDict[str, t.DefaultDict[str, t.Dict[str, str]]]:
    """
    Return the collections with their plugins for every plugin type.

    :arg plugin_info: Mapping of plugin type to a mapping of plugin name to plugin record.
        The plugin_type, plugin_name, and short_description from plugin_records are used.
    :arg nonfatal_errors: mapping of plugin type to plugin name to list of error messages.
        The plugin_type and plugin_name are used.
    :returns: A Mapping of plugin type to a mapping of collection name to a mapping of plugin names
        to short_descriptions.
    plugin_type:
        collection:
            - plugin_short_name: short_description
    """
    plugin_contents = defaultdict(lambda: defaultdict(dict))
    # Some plugins won't have an entry in the plugin_info because documentation failed to parse.
    # Those should be documented in the nonfatal_errors information.
    for plugin_type, plugin_list in nonfatal_errors.items():
        for plugin_name, dummy_ in plugin_list.items():
            namespace, collection, short_name = get_fqcn_parts(plugin_name)
            plugin_contents[plugin_type]['.'.join((namespace, collection))][short_name] = ''

    for plugin_type, plugin_list in plugin_info.items():
        for plugin_name, plugin_desc in plugin_list.items():
            namespace, collection, short_name = get_fqcn_parts(plugin_name)
            plugin_contents[plugin_type]['.'.join((namespace, collection))][short_name] = (
                plugin_desc['doc']['short_description'])

    return plugin_contents


def get_collection_contents(plugin_content: t.Mapping[str, t.Mapping[str, t.Mapping[str, str]]],
                            ) -> t.DefaultDict[str, t.Dict[str, t.Mapping[str, str]]]:
    """
    Return the plugins which are in each collection.

    :arg plugin_content: Mapping of plugin type to a mapping of collection name to a mapping of
        plugin name to short description.
    :returns: A Mapping of collection name to a mapping of plugin type to a mapping of plugin names
        to short_descriptions.
    collection:
        plugin_type:
            - plugin_short_name: short_description
    """
    collection_plugins = defaultdict(dict)

    for plugin_type, collection_data in plugin_content.items():
        for collection_name, plugin_data in collection_data.items():
            collection_plugins[collection_name][plugin_type] = plugin_data

    return collection_plugins


def generate_docs_for_all_collections(venv: t.Union[VenvRunner, FakeVenvRunner],
                                      collection_dir: t.Optional[str],
                                      dest_dir: str,
                                      collection_names: t.Optional[t.List[str]] = None,
                                      create_indexes: bool = True,
                                      squash_hierarchy: bool = False,
                                      breadcrumbs: bool = True) -> None:
    """
    Create documentation for a set of installed collections.

    :arg venv: The venv in which ansible-base is installed.
    :arg collection_dir: The directory in which the collections have been installed.
                         If ``None``, the collections are assumed to be in the current
                         search path for Ansible.
    :arg dest_dir: The directory into which the documentation is written.
    :kwarg collection_names: Optional list of collection names. If specified, only documentation
                             for these collections will be collected and generated.
    :kwarg create_indexes: Whether to create the collection, namespace, and plugin indexes. By
                           default, they are created.
    :kwarg squash_hierarchy: If set to ``True``, no directory hierarchy will be used.
                             Undefined behavior if documentation for multiple collections are
                             created.
    :kwarg breadcrumbs: Default True.  Set to False if breadcrumbs for collections should be
        disabled.  This will disable breadcrumbs but save on memory usage.
    """
    flog = mlog.fields(func='generate_docs_for_all_collections')
    flog.notice('Begin')

    # Get the info from the plugins
    plugin_info, collection_metadata = asyncio_run(get_ansible_plugin_info(
        venv, collection_dir, collection_names=collection_names))
    flog.notice('Finished parsing info from plugins and collections')
    # flog.fields(plugin_info=plugin_info).debug('Plugin data')
    # flog.fields(
    #     collection_metadata=collection_metadata).debug('Collection metadata')

    # Load collection routing information
    collection_routing = asyncio_run(load_all_collection_routing(collection_metadata))
    flog.notice('Finished loading collection routing information')
    # flog.fields(collection_routing=collection_routing).debug('Collection routing infos')

    remove_redirect_duplicates(plugin_info, collection_routing)
    stubs_info = find_stubs(plugin_info, collection_routing)
    # flog.fields(stubs_info=stubs_info).debug('Stubs info')

    plugin_info, nonfatal_errors = asyncio_run(normalize_all_plugin_info(plugin_info))
    flog.fields(errors=len(nonfatal_errors)).notice('Finished data validation')
    augment_docs(plugin_info)
    flog.notice('Finished calculating new data')

    # Load collection extra docs data
    extra_docs_data = asyncio_run(load_collections_extra_docs(
        {name: data.path for name, data in collection_metadata.items()}))
    flog.debug('Finished getting collection extra docs data')

    plugin_contents = get_plugin_contents(plugin_info, nonfatal_errors)
    collection_to_plugin_info = get_collection_contents(plugin_contents)
    # Make sure collections without documentable plugins are mentioned
    for collection in collection_metadata:
        collection_to_plugin_info[collection]
    flog.debug('Finished getting collection data')

    collection_namespaces = get_collection_namespaces(collection_to_plugin_info.keys())

    # Only build top-level index if requested
    if create_indexes:
        asyncio_run(output_collection_index(
            collection_to_plugin_info, collection_namespaces, dest_dir, breadcrumbs=breadcrumbs))
        flog.notice('Finished writing collection index')
        asyncio_run(output_collection_namespace_indexes(collection_namespaces, dest_dir,
                                                        breadcrumbs=breadcrumbs))
        flog.notice('Finished writing collection namespace index')
        asyncio_run(output_plugin_indexes(plugin_contents, dest_dir))
        flog.notice('Finished writing plugin indexes')

    asyncio_run(output_indexes(collection_to_plugin_info, dest_dir,
                               collection_metadata=collection_metadata,
                               squash_hierarchy=squash_hierarchy,
                               extra_docs_data=extra_docs_data,
                               breadcrumbs=breadcrumbs))
    flog.notice('Finished writing indexes')

    asyncio_run(output_all_plugin_stub_rst(stubs_info, dest_dir,
                                           collection_metadata=collection_metadata,
                                           squash_hierarchy=squash_hierarchy))
    flog.debug('Finished writing plugin stubs')

    asyncio_run(output_all_plugin_rst(collection_to_plugin_info, plugin_info,
                                      nonfatal_errors, dest_dir,
                                      collection_metadata=collection_metadata,
                                      squash_hierarchy=squash_hierarchy))
    flog.debug('Finished writing plugin docs')

    asyncio_run(output_extra_docs(dest_dir, extra_docs_data,
                                  squash_hierarchy=squash_hierarchy))
    flog.debug('Finished writing extra extra docs docs')


def generate_docs() -> int:
    """
    Create documentation for the stable subcommand.

    Stable documentation creates documentation for a built version of Ansible.  It uses the exact
    versions of collections included in the last Ansible release to generate rst files documenting
    those collections.

    :returns: A return code for the program.  See :func:`antsibull.cli.antsibull_docs.main` for
        details on what each code means.
    """
    flog = mlog.fields(func='generate_docs')
    flog.notice('Begin generating docs')

    app_ctx = app_context.app_ctx.get()

    # Parse the deps file
    flog.fields(deps_file=app_ctx.extra['deps_file']).info('Parse deps file')
    deps_file = DepsFile(app_ctx.extra['deps_file'])
    dummy_, ansible_base_version, collections = deps_file.parse()
    flog.debug('Finished parsing deps file')

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Retrieve ansible-base and the collections
        flog.fields(tmp_dir=tmp_dir).info('created tmpdir')
        collection_tarballs = asyncio_run(
            retrieve(ansible_base_version, collections, tmp_dir,
                     galaxy_server=app_ctx.galaxy_url,
                     ansible_base_source=app_ctx.extra['ansible_base_source'],
                     collection_cache=app_ctx.extra['collection_cache']))
        # flog.fields(tarballs=collection_tarballs).debug('Download complete')
        flog.notice('Finished retrieving tarballs')

        # Get the ansible-core location
        try:
            ansible_base_path = collection_tarballs.pop('_ansible_base')
        except KeyError:
            print('ansible-core did not download successfully')
            return 3
        flog.fields(ansible_base_path=ansible_base_path).info('ansible-core location')

        # Install the collections to a directory

        # Directory that ansible needs to see
        collection_dir = os.path.join(tmp_dir, 'installed')
        # Directory that the collections will be untarred inside of
        collection_install_dir = os.path.join(collection_dir, 'ansible_collections')
        # Safe to recursively mkdir because we created the tmp_dir
        os.makedirs(collection_install_dir, mode=0o700)
        flog.fields(collection_install_dir=collection_install_dir).debug('collection install dir')

        # Install the collections
        asyncio_run(install_together(collection_tarballs.values(), collection_install_dir))
        flog.notice('Finished installing collections')

        # Create venv for ansible-core
        venv = VenvRunner('ansible-core-venv', tmp_dir)
        venv.install_package(ansible_base_path)
        flog.fields(venv=venv).notice('Finished installing ansible-core')

        generate_docs_for_all_collections(venv, collection_dir, app_ctx.extra['dest_dir'],
                                          breadcrumbs=app_ctx.breadcrumbs)

    return 0
