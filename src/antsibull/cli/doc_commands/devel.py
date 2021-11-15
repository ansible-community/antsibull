# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

import asyncio
import os
import os.path
import tempfile
import typing as t

import aiohttp
import asyncio_pool

from .stable import generate_docs_for_all_collections
from ... import app_context
from ...ansible_base import get_ansible_base
from ...collections import install_together
from ...compat import asyncio_run
from ...dependency_files import parse_pieces_file
from ...galaxy import CollectionDownloader, DownloadResults
from ...logging import log
from ...venv import VenvRunner

if t.TYPE_CHECKING:
    import semantic_version as semver


mlog = log.fields(mod=__name__)


async def retrieve(collections: t.List[str],
                   tmp_dir: str,
                   galaxy_server: str,
                   ansible_base_source: t.Optional[str] = None,
                   collection_cache: t.Optional[str] = None) -> t.Dict[str, 'semver.Version']:
    """
    Download ansible-core and the latest versions of the collections.

    :arg collections: List of collection names to download.
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
                get_ansible_base(aio_session, '@devel', tmp_dir,
                                 ansible_base_source=ansible_base_source))

            downloader = CollectionDownloader(aio_session, collection_dir,
                                              galaxy_server=galaxy_server,
                                              collection_cache=collection_cache)
            for collection in collections:
                requestors[collection] = await pool.spawn(
                    downloader.download_latest_matching(collection, '*'))

            responses = await asyncio.gather(*requestors.values())

    responses = [
        data.download_path if isinstance(data, DownloadResults) else data for data in responses
    ]
    # Note: Python dicts have always had a stable order as long as you don't modify the dict.
    # So requestors (implicitly, the keys) and responses have a matching order here.
    return dict(zip(requestors, responses))


def generate_docs() -> int:
    """
    Create documentation for the devel subcommand.

    Devel documentation creates documentation for the current development version of Ansible.
    It uses the latest collection releases for the collections mentioned in the specified pieces
    file to generate rst files documenting those collections.

    :returns: A return code for the program.  See :func:`antsibull.cli.antsibull_docs.main` for
        details on what each code means.
    """
    flog = mlog.fields(func='generate_docs')
    flog.notice('Begin generating docs')

    app_ctx = app_context.app_ctx.get()

    # Parse the pieces file
    flog.fields(deps_file=app_ctx.extra['pieces_file']).info('Parse pieces file')
    collections = parse_pieces_file(app_ctx.extra['pieces_file'])
    flog.debug('Finished parsing deps file')

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Retrieve ansible-base and the collections
        flog.fields(tmp_dir=tmp_dir).info('created tmpdir')
        collection_tarballs = asyncio_run(
            retrieve(collections, tmp_dir,
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
