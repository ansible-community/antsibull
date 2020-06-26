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

from ...ansible_base import get_ansible_base
from ...augment_docs import augment_docs
from ...collections import install_together
from ...compat import asyncio_run, best_get_loop
from ...constants import PROCESS_MAX, THREAD_MAX
from ...dependency_files import DepsFile
from ...docs_parsing.ansible_doc import get_ansible_plugin_info
from ...docs_parsing.fqcn import get_fqcn_parts
from ...galaxy import CollectionDownloader
from ...logging import log
from ...schemas.docs import DOCS_SCHEMAS
from ...venv import VenvRunner
from ...write_docs import output_all_plugin_rst, output_indexes

if t.TYPE_CHECKING:
    import argparse
    import semantic_version as semver


mlog = log.fields(mod=__name__)

#: Mapping of plugins to nonfatal errors.  This is the type to use when returning the mapping.
PluginErrorsRT = t.DefaultDict[str, t.DefaultDict[str, t.List[str]]]


async def retrieve(ansible_base_version: str,
                   collections: t.Mapping[str, str],
                   tmp_dir: str,
                   ansible_base_cache: t.Optional[str] = None,
                   collection_cache: t.Optional[str] = None) -> t.Dict[str, 'semver.Version']:
    """
    Download ansible-base and the collections.

    :arg ansible_base_version: Version of ansible-base to download.
    :arg collections: Map of collection names to collection versions to download.
    :arg tmp_dir: The directory to download into
    :kwarg ansible_base_cache: If given, a path to an Ansible-base checkout or expanded sdist.
        This will be used instead of downloading an ansible-base package if the version matches
        with ``ansible_base_version``.
    :kwarg collection_cache: If given, a path to a directory containing collection tarballs.
        These tarballs will be used instead of downloading new tarballs provided that the
        versions match the criteria (latest compatible version known to galaxy).
    :returns: Map of collection name to directory it is in.  ansible-base will
        use the special key, `_ansible_base`.
    """
    collection_dir = os.path.join(tmp_dir, 'collections')
    os.mkdir(collection_dir, mode=0o700)

    requestors = {}
    async with aiohttp.ClientSession() as aio_session:
        async with asyncio_pool.AioPool(size=THREAD_MAX) as pool:
            requestors['_ansible_base'] = await pool.spawn(
                get_ansible_base(aio_session, ansible_base_version, tmp_dir,
                                 ansible_base_cache=ansible_base_cache))

            downloader = CollectionDownloader(aio_session, collection_dir,
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
        See the schema in :mod:`antsibull.schemas` for what the data should look like and just how
        much conversion we can perform on it.
    :returns: A tuple containing a "copy" of plugin_info with all of the data normalized and a list
        of nonfatal errors.  The plugin_info dict will follow the structure expressed in the schemas
        in :mod:`antsibull.schemas`.  The nonfatal errors are strings representing the problems
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
        the plugins that are to be documented. See the schema in :mod:`antsibull.schemas` for the
        structure of the information.
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
    executor = ProcessPoolExecutor(max_workers=PROCESS_MAX)

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


def get_collection_contents(plugin_info: t.Mapping[str, t.Mapping[str, t.Any]],
                            nonfatal_errors: PluginErrorsRT
                            ) -> t.DefaultDict[str, t.DefaultDict[str, t.Dict[str, str]]]:
    """
    Return the plugins which are in each collection.

    :arg plugin_info: Mapping of plugin type to a mapping of plugin name to plugin record.
        The plugin_type, plugin_name, and short_description from plugin_records are used.
    :arg nonfatal_errors: mapping of plugin type to plugin name to list of error messages.
        The plugin_type and plugin_name are used.
    :returns: A Mapping of collection name to a mapping of plugin type to a mapping of plugin names
        to short_descriptions.
    collection:
        plugin_type:
            - plugin_short_name: short_description
    """
    collection_plugins = defaultdict(lambda: defaultdict(dict))
    # Some plugins won't have an entry in the plugin_info because documentation failed to parse.
    # Those should be documented in the nonfatal_errors information.
    for plugin_type, plugin_list in nonfatal_errors.items():
        for plugin_name, dummy_ in plugin_list.items():
            namespace, collection, short_name = get_fqcn_parts(plugin_name)
            collection_plugins['.'.join((namespace, collection))][plugin_type][short_name] = ''

    for plugin_type, plugin_list in plugin_info.items():
        for plugin_name, plugin_desc in plugin_list.items():
            namespace, collection, short_name = get_fqcn_parts(plugin_name)
            collection_plugins['.'.join((namespace, collection))][plugin_type][short_name] = (
                plugin_desc['doc']['short_description'])

    return collection_plugins


def generate_docs(args: 'argparse.Namespace') -> int:
    """
    Create documentation for the stable subcommand.

    Stable documentation creates documentation for a built version of Ansible.  It uses the exact
    versions of collections included in the last Ansible release to generate rst files documenting
    those collections.

    :arg args: The parsed comand line args.
    :returns: A return code for the program.  See :func:`antsibull.cli.antsibull_docs.main` for
        details on what each code means.
    """
    flog = mlog.fields(func='generate_docs')
    flog.debug('Begin processing docs')

    # Parse the deps file
    deps_file = DepsFile(args.deps_file)
    dummy_, ansible_base_version, collections = deps_file.parse()
    flog.debug('Finished parsing deps file')

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Retrieve ansible-base and the collections
        collection_tarballs = asyncio_run(retrieve(ansible_base_version, collections, tmp_dir,
                                                   ansible_base_cache=args.ansible_base_cache,
                                                   collection_cache=args.collection_cache))
        flog.debug('Finished retrieving tarballs')

        # Get the ansible-base location
        try:
            # Note, this may be a tarball or the path to an ansible-base checkout/expanded sdist.
            ansible_base_path = collection_tarballs.pop('_ansible_base')
        except KeyError:
            print('ansible-base did not download successfully')
            return 3

        # Install the collections to a directory

        # Directory that ansible needs to see
        collection_dir = os.path.join(tmp_dir, 'installed')
        # Directory that the collections will be untarred inside of
        collection_install_dir = os.path.join(collection_dir, 'ansible_collections')
        # Safe to recursively mkdir because we created the tmp_dir
        os.makedirs(collection_install_dir, mode=0o700)

        # Install the collections
        asyncio_run(install_together(collection_tarballs.values(), collection_install_dir))
        flog.debug('Finished installing collections')

        # Create venv for ansible-base
        venv = VenvRunner('ansible-base-venv', tmp_dir)
        if os.path.isdir(ansible_base_path):
            venv.install_package(ansible_base_path, from_project_path=True)
        else:
            venv.install_package(ansible_base_path)
        flog.debug('Finished installing ansible-base')

        # Get the data on every plugin
        plugin_info = asyncio_run(get_ansible_plugin_info(venv, collection_dir))
        flog.debug('Finished parsing info from plugins')

        """
        # Turn these into some sort of decorator that will choose to dump or load the values
        # if a command line arg is specified.
        with open('dump_raw_plugin_info.json', 'w') as f:
            import json
            json.dump(plugin_info, f)
        flog.debug('Finished dumping raw plugin_info')

        with open('dump_formatted_plugin_info.json', 'r') as f:
            import json
            plugin_info = json.load(f)
        """

        plugin_info, nonfatal_errors = asyncio_run(normalize_all_plugin_info(plugin_info))
        flog.debug('Finished normalizing data')
        augment_docs(plugin_info)

        """
        with open('dump_normalized_plugin_info.json', 'w') as f:
            json.dump(plugin_info, f)
        flog.debug('Finished dumping normalized data')

        with open('dump_errors.json', 'w') as f:
            json.dump(nonfatal_errors, f)
        flog.debug('Finished dump errors')

        with open('dump_normalized_plugin_info.json', 'r') as f:
            import json
            plugin_info = json.load(f)
        flog.debug('Finished loading normalized data')

        with open('dump_errors.json', 'r') as f:
            from collections import defaultdict
            nonfatal_errors = json.load(f)
            nonfatal_errors = defaultdict(lambda: defaultdict(list), nonfatal_errors)
            for key, value in nonfatal_errors.items():
                nonfatal_errors[key] = defaultdict(list, value)
        flog.debug('Finished loading errors')
        """

        collection_info = get_collection_contents(plugin_info, nonfatal_errors)
        flog.debug('Finished extracting collection data')

        asyncio_run(output_indexes(collection_info, args.dest_dir))
        flog.debug('Finished writing indexes')

        asyncio_run(output_all_plugin_rst(collection_info, plugin_info,
                                          nonfatal_errors, args.dest_dir))
        flog.debug('Finished writing plugin docs')

    return 0
