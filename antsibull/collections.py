# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functions to deal with collections on the local system"""
import asyncio
import os
from typing import List

import sh

from .compat import best_get_loop


class CollectionFormatError(Exception):
    pass


async def install_together(collection_tarballs: List[str],
                           ansible_collections_dir: str) -> None:
    loop = best_get_loop()

    installers = []
    for pathname in collection_tarballs:
        namespace, collection, _dummy = os.path.basename(pathname).split('-', 2)
        collection_dir = os.path.join(ansible_collections_dir, namespace, collection)
        # Note: mkdir -p equivalent is okay because we created package_dir ourselves as a directory
        # that only we can access
        os.makedirs(collection_dir, mode=0o700, exist_ok=False)

        # If the choice of install tools for galaxy is ever settled upon, we can switch from tar to
        # using that
        # sh dynamically creates functions which map to executables
        # pyre-ignore[16]
        installers.append(loop.run_in_executor(None, sh.tar, '-xf', pathname, '-C', collection_dir))

    await asyncio.gather(*installers)


async def install_separately(collection_tarballs: List[str], collection_dir: str) -> List:
    loop = asyncio.get_running_loop()

    installers = []
    collection_dirs = []

    if not collection_tarballs:
        return collection_dirs

    for pathname in collection_tarballs:
        filename = os.path.basename(pathname)
        namespace, collection, version_ext = filename.split('-', 2)
        version = None
        for ext in ('.tar.gz',):
            # Note: If galaxy allows other archive formats, add their extensions here
            ext_start = version_ext.find(ext)
            if ext_start != -1:
                version = version_ext[:ext_start]
                break
        else:
            raise CollectionFormatError('Collection filename was in an unexpected'
                                        f' format: {filename}')

        package_dir = os.path.join(collection_dir, f'ansible-collections-{namespace}.'
                                   f'{collection}-{version}')
        os.mkdir(package_dir, mode=0o700)
        collection_dirs.append(package_dir)

        collection_dir = os.path.join(package_dir, 'ansible_collections', namespace, collection)
        # Note: this is okay because we created package_dir ourselves as a directory
        # that only we can access
        os.makedirs(collection_dir, mode=0o700, exist_ok=False)

        # If the choice of install tools for galaxy is ever settled upon, we can switch from tar to
        # using that
        # sh dynamically creates functions which map to executables
        # pyre-ignore[16]
        installers.append(loop.run_in_executor(None, sh.tar, '-xf', pathname,
                                               '-C', collection_dir))

    await asyncio.gather(*installers)

    return collection_dirs
