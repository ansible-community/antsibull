# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2021
"""Handle collection-specific links from galaxy.yml and docs/docsite/links.yml."""

import asyncio
import json
import os
import os.path
import typing as t

import asyncio_pool

from pydantic import Extra
from pydantic.error_wrappers import ValidationError, display_errors

from . import app_context
from .logging import log
from .yaml import load_yaml_file
from .schemas.collection_links import (
    CollectionEditOnGitHub,
    Link,
    IRCChannel,
    MatrixRoom,
    MailingList,
    Communication,
    CollectionLinks,
)


mlog = log.fields(mod=__name__)


_ANSIBLE_CORE_METADATA = dict(
    edit_on_github=dict(
        repository='ansible/ansible',
        branch='devel',
        path_prefix='lib/ansible/',
    ),
    authors=['Ansible, Inc.'],
    description='These are all modules and plugins contained in ansible-core.',
    links=[
        dict(description='Issue Tracker', url='https://github.com/ansible/ansible/issues'),
        dict(description='Repository (Sources)', url='https://github.com/ansible/ansible'),
    ],
    communication=dict(
        irc_channels=[dict(
            topic='General usage and support questions',
            network='Libera',
            channel='#ansible',
        )],
        matrix_rooms=[dict(
            topic='General usage and support questions',
            room='#users:ansible.im',
        )],
        mailing_lists=[dict(
            topic='Ansible Project List',
            url='https://groups.google.com/g/ansible-project',
        )],
    ),
)


def _extract_authors(data: t.Dict) -> t.List[str]:
    authors = data.get('authors')
    if not isinstance(authors, list):
        return []

    return [str(author) for author in authors]


def _extract_description(data: t.Dict) -> t.Optional[str]:
    desc = data.get('description')
    return desc if isinstance(desc, str) else None


def _extract_galaxy_links(data: t.Dict) -> t.List[Link]:
    result = []

    def extract(key: str, desc: str,
                not_if_equals_one_of: t.Optional[t.List[str]] = None) -> None:
        url = data.get(key)
        if not_if_equals_one_of:
            for other_key in not_if_equals_one_of:
                if data.get(other_key) == url:
                    return
        if isinstance(url, str):
            result.append(Link.parse_obj(dict(description=desc, url=url)))

    # extract('documentation', 'Documentation')
    extract('issues', 'Issue Tracker')
    extract('homepage', 'Homepage', not_if_equals_one_of=['documentation', 'repository'])
    extract('repository', 'Repository (Sources)')
    return result


def load(links_data: t.Optional[t.Dict], galaxy_data: t.Optional[t.Dict],
         manifest_data: t.Optional[t.Dict]) -> CollectionLinks:
    if links_data:
        ld = links_data.copy()
        # The authors and description field always comes from collection metadata
        ld.pop('authors', None)
        ld.pop('description', None)
        # Links only comes in directly
        ld.pop('links', None)
    else:
        ld = {}
    try:
        result = CollectionLinks.parse_obj(ld)
    except ValidationError:
        result = CollectionLinks.parse_obj({})

    # Parse MANIFEST or galaxy data
    if isinstance(manifest_data, dict):
        collection_info = manifest_data.get('collection_info')
        if isinstance(collection_info, dict):
            result.authors = _extract_authors(collection_info)
            result.description = _extract_description(collection_info)
            result.links.extend(_extract_galaxy_links(collection_info))
    elif isinstance(galaxy_data, dict):
        result.authors = _extract_authors(galaxy_data)
        result.description = _extract_description(galaxy_data)
        result.links.extend(_extract_galaxy_links(galaxy_data))

    result.links.extend(result.extra_links)

    return result


async def load_collection_links(collection_name: str,
                                collection_path: str,
                                ) -> CollectionLinks:
    '''Given a collection name and path, load links data.

    :arg collection_name: Dotted collection name.
    :arg collection_path: Path to the collection.
    :returns: A CollectionLinks instance.
    '''
    flog = mlog.fields(func='load_collection_links')
    flog.debug('Enter')

    if collection_name == 'ansible.builtin':
        return CollectionLinks.parse_obj(_ANSIBLE_CORE_METADATA)

    try:
        # Load links data
        index_path = os.path.join(collection_path, 'docs', 'docsite', 'links.yml')
        links_data = None
        if os.path.isfile(index_path):
            links_data = load_yaml_file(index_path)

        # Load galaxy.yml
        galaxy_data = None
        galaxy_path = os.path.join(collection_path, 'galaxy.yml')
        if os.path.isfile(galaxy_path):
            galaxy_data = load_yaml_file(galaxy_path)

        # Load MANIFEST.json
        manifest_data = None
        manifest_path = os.path.join(collection_path, 'MANIFEST.json')
        if os.path.isfile(manifest_path):
            with open(manifest_path, 'rb') as f:
                manifest_data = json.loads(f.read())

        return load(links_data=links_data, galaxy_data=galaxy_data, manifest_data=manifest_data)
    finally:
        flog.debug('Leave')


async def load_collections_links(collection_paths: t.Mapping[str, str]
                                 ) -> t.Mapping[str, CollectionLinks]:
    '''Load links data.

    :arg collection_paths: Mapping of collection_name to the collection's path.
    :returns: A mapping of collection_name to CollectionLinks.
    '''
    flog = mlog.fields(func='load_collections_links')
    flog.debug('Enter')

    loaders = {}
    lib_ctx = app_context.lib_ctx.get()

    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        for collection_name, collection_path in collection_paths.items():
            loaders[collection_name] = await pool.spawn(
                load_collection_links(collection_name, collection_path))

        responses = await asyncio.gather(*loaders.values())

    # Note: Python dicts have always had a stable order as long as you don't modify the dict.
    # So loaders (implicitly, the keys) and responses have a matching order here.
    result = dict(zip(loaders, responses))

    flog.debug('Leave')
    return result


def lint_collection_links(collection_path: str) -> t.List[t.Tuple[str, int, int, str]]:
    '''Given a path, lint links data.

    :arg collection_path: Path to the collection.
    :returns: List of tuples (filename, row, column, error) indicating linting errors.
    '''
    flog = mlog.fields(func='lint_collection_links')
    flog.debug('Enter')

    result = []

    for cls in (
            CollectionEditOnGitHub, Link, IRCChannel, MatrixRoom, MailingList, Communication,
            CollectionLinks,
    ):
        cls.__config__.extra = Extra.forbid

    try:
        index_path = os.path.join(collection_path, 'docs', 'docsite', 'links.yml')
        if not os.path.isfile(index_path):
            return result

        links_data = load_yaml_file(index_path)
        for forbidden_key in ('authors', 'description', 'links'):
            if forbidden_key in links_data:
                result.append((index_path, 0, 0, f"The key '{forbidden_key}' must not be used"))
        try:
            CollectionLinks.parse_obj(links_data)
        except ValidationError as exc:
            for error in exc.errors():
                result.append((index_path, 0, 0, display_errors([error]).replace('\n ', ':')))

        return result
    finally:
        flog.debug('Leave')
