# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2022 Maxwell G <gotmax@e.email>

"""
Validate that collections tag their releases in their respective git repositories
"""
import asyncio
import os
import re
import sys
import typing as t

import asyncio_pool  # type: ignore[import]

from antsibull_core.logging import log

from antsibull_core import app_context
from antsibull_core.dependency_files import DepsFile
from antsibull_core.yaml import store_yaml_file, load_yaml_file

from antsibull.collection_meta import CollectionsMetadata

TAG_MATCHER: t.Pattern[str] = re.compile(r'^.*refs/tags/(.*)$')
mlog = log.fields(mod=__name__)


def validate_tags_command() -> int:
    app_ctx = app_context.app_ctx.get()
    if app_ctx.extra['input']:
        tag_data = load_yaml_file(app_ctx.extra['input'])
    else:
        tag_data = asyncio.run(get_collections_tags())
        if app_ctx.extra['output']:
            store_yaml_file(app_ctx.extra['output'], tag_data)
    errors = validate_tags(tag_data)
    if not errors:
        return 0
    for error in errors:
        print(error, file=sys.stderr)
    return 1


def validate_tags(tag_data: t.Dict[str, t.Dict[str, t.Optional[str]]]) -> t.List[str]:
    errors = []
    for name, data in tag_data.items():
        if not data['repository']:
            errors.append(
                f"{name}'s repository is not specified at all in collection-meta.yaml"
            )
            continue
        if not data['tag']:
            errors.append(
                f"{name} {data['version']} is not tagged in "
                f"{data['repository']}"
            )
    return errors


async def get_collections_tags() -> t.Dict[str, t.Dict[str, t.Optional[str]]]:
    app_ctx = app_context.app_ctx.get()
    lib_ctx = app_context.lib_ctx.get()

    deps_filename = os.path.join(
        app_ctx.extra['data_dir'], app_ctx.extra['deps_file']
    )
    deps_data = DepsFile(deps_filename).parse()
    meta_data = CollectionsMetadata(app_ctx.extra['data_dir'])

    async with asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool:
        collection_tags = {}
        for name, data in meta_data.data.items():
            collection_tags[name] = pool.spawn_n(
                _get_collection_tags(deps_data.deps[name], data)
            )
        collection_tags = {
            name: await data for name, data in collection_tags.items()
        }
        return collection_tags


async def _get_collection_tags(
    version: str, meta_data=t.Dict[str, t.Optional[str]]
) -> t.Dict[str, t.Optional[str]]:
    flog = mlog.fields(func='_get_collection_tags')
    repository = meta_data.repository
    data: t.Dict[str, t.Optional[str]] = dict(
        version=version, repository=repository, tag=None
    )
    if meta_data.collection_directory:
        data['collection_directory'] = meta_data.collection_directory
    if not repository:
        flog.debug("'repository' is None. Exitting...")
        return data
    async for tag in _get_tags(repository):
        if _normalize_tag(tag) == version:
            data['tag'] = tag
            break
    return data


async def _get_tags(repository) -> t.AsyncGenerator[str, None]:
    flog = mlog.fields(func='_get_tags')
    args = (
        'git',
        'ls-remote',
        '--refs',
        '--tags',
        repository,
    )
    flog.debug(f'Running {args}')
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    flog.fields(stderr=stderr).debug('Ran git ls-remote')
    if proc.returncode != 0:
        flog.error(f'Failed to fetch tags for {repository}')
        return
    tags: t.List[str] = stdout.decode('utf-8').splitlines()
    if not tags:
        flog.warning(f'{repository} does not have any tags')
        return
    for tag in tags:
        match = TAG_MATCHER.match(tag)
        if match:
            yield match.group(1)
        else:
            flog.debug(f'git ls-remote output line skipped: {tag}')


def _normalize_tag(tag: str) -> str:
    if tag.startswith('v'):
        tag = tag[1:]
    return tag
