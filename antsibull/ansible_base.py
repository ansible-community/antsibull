# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functions for working with the ansible-base package."""
import ast
import os
import re
import typing as t
from functools import lru_cache
from urllib.parse import urljoin

import aiofiles
import packaging.version as pypiver
import sh

from .compat import best_get_loop
from .constants import CHUNKSIZE

if t.TYPE_CHECKING:
    import aiohttp.client


#: URL to checkout ansible-base from.
ANSIBLE_BASE_URL = 'https://github.com/ansible/ansible'
#: URL to pypi.
PYPI_SERVER_URL = 'https://test.pypi.org/'


class UnknownVersion(Exception):
    """Raised when a requested version does not exist."""


class AnsibleBasePyPiClient:
    """Class to retrieve information about AnsibleBase from Pypi."""

    def __init__(self, aio_session: 'aiohttp.client.ClientSession',
                 pypi_server_url: str = PYPI_SERVER_URL) -> None:
        """
        Initialize the AnsibleBasePypi class.

        :arg aio_session: :obj:`aiohttp.client.ClientSession` to make requests to pypi from.
        :kwarg pypi_server_url: URL to the pypi server to use.
        """
        self.aio_session = aio_session
        self.pypi_server_url = pypi_server_url

    @lru_cache(None)
    async def get_info(self) -> t.Dict[str, t.Any]:
        """
        Retrieve information about the ansible-base package from pypi.

        :returns: The dict which represents the information about the ansible-base package returned
            from pypi.  To examine the data structure, use::

                curl https://pypi.org/pypi/ansible-base/json| python3 -m json.tool
        """
        # Retrieve the ansible-base package info from pypi
        query_url = urljoin(self.pypi_server_url, 'pypi/ansible-base/json')
        async with self.aio_session.get(query_url) as response:
            pkg_info = await response.json()
        return pkg_info

    async def get_versions(self) -> t.List[pypiver.Version]:
        """
        Get the versions of the ansible-base package on pypi.

        :returns: A list of :pypkg:obj:`packaging.versioning.Version`s
            for all the versions on pypi, including prereleases.
        """
        pkg_info = await self.get_info()
        versions = [pypiver.Version(r) for r in pkg_info['releases']]
        versions.sort(reverse=True)
        return versions

    async def get_latest_version(self) -> pypiver.Version:
        """
        Get the latest version of ansible-base uploaded to pypi.

        :return: A :pypkg:obj:`packaging.versioning.Version` object representing the latest version
            of the package on pypi.  This may be a pre-release.
        """
        versions = await self.get_versions()
        return versions[0]

    async def retrieve(self, ansible_base_version: t.Union[str, pypiver.Version],
                       download_dir: str) -> str:
        """
        Get the release from pypi.

        :arg ansible_base_version: Version of ansible-base to download.
        :arg download_dir: Directory to download the tarball to.
        :returns: The name of the downloaded tarball.
        """
        pkg_info = await self.get_info()

        pypi_url = tar_filename = ''
        for release in pkg_info['releases'][ansible_base_version]:
            if release['filename'].startswith(f'ansible-base-{ansible_base_version}.tar.'):
                tar_filename = release['filename']
                pypi_url = release['url']
                break
        else:  # for-else: http://bit.ly/1ElPkyg
            raise UnknownVersion(f'ansible-base {ansible_base_version} does not'
                                 ' exist on {pypi_server_url}')

        tar_filename = os.path.join(download_dir, tar_filename)
        async with self.aio_session.get(pypi_url) as response:
            async with aiofiles.open(tar_filename, 'wb') as f:
                # TODO: PY3.8: while chunk := await response.read(CHUNKSIZE):
                chunk = await response.content.read(CHUNKSIZE)
                while chunk:
                    await f.write(chunk)
                    chunk = await response.content.read(CHUNKSIZE)

        return tar_filename


def _get_cache_version(ansible_base_cache: str) -> pypiver.Version:
    with open(os.path.join(ansible_base_cache, 'lib', 'ansible', 'release.py')) as f:
        root = ast.parse(f.read())

    # Find the version of the cache
    cache_version = None
    # Iterate backwards in case __version__ is assigned to multiple times
    for node in reversed(root.body):
        if isinstance(node, ast.Assign):
            for name in node.targets:
                # These attributes are dynamic so pyre cannot check them
                if name.id == '__version__':  # pyre-ignore[16]
                    cache_version = node.value.s  # pyre-ignore[16]
                    break

        if cache_version:
            break

    if not cache_version:
        raise ValueError('Version was not found')

    return pypiver.Version(cache_version)


def cache_is_devel(ansible_base_cache: t.Optional[str]) -> bool:
    """
    :arg ansible_base_cache: A path to an Ansible-base checkout or expanded sdist or None.
        This will be used instead of downloading an ansible-base package if the version matches
        with ``ansible_base_version``.
    :returns: True if the cache looks like it is for the devel branch.
    """
    if ansible_base_cache is None:
        return False

    try:
        cache_version = _get_cache_version(ansible_base_cache)
    except Exception:
        return False

    dev_version = re.compile('[.]dev[0-9]+$')
    if dev_version.match(cache_version.public):
        return True

    return False


def cache_is_correct_version(ansible_base_cache: t.Optional[str],
                             ansible_base_version: pypiver.Version) -> bool:
    """
    :arg ansible_base_cache: A path to an Ansible-base checkout or expanded sdist or None.
        This will be used instead of downloading an ansible-base package if the version matches
        with ``ansible_base_version``.
    :arg ansible_base_version: Version of ansible-base to retrieve.
    :returns: True if the cache is for a compatible version at or newer than the requested version
    """
    if ansible_base_cache is None:
        return False

    try:
        cache_version = _get_cache_version(ansible_base_cache)
    except Exception:
        return False

    # If the cache is a compatible version of ansible-base and it is the same or more recent than
    # the requested version then allow this.
    if (cache_version.major == ansible_base_version.major
            and cache_version.minor == ansible_base_version.minor
            and cache_version.micro >= ansible_base_version.micro):
        return True

    return False


@lru_cache(None)
async def checkout_from_git(download_dir: str, repo_url: str = ANSIBLE_BASE_URL) -> str:
    """
    Checkout the ansible-base git repo.

    :arg download_dir: Directory to checkout into.
    :kwarg: repo_url: The url to the git repo.
    :return: The directory that ansible-base has been checked out to.
    """
    loop = best_get_loop()
    ansible_base_dir = os.path.join(download_dir, 'ansible-base')
    await loop.run_in_executor(None, sh.git, 'clone', repo_url, ansible_base_dir)

    return ansible_base_dir


async def get_ansible_base(aio_session: 'aiohttp.client.ClientSession',
                           ansible_base_version: str,
                           tmpdir: str,
                           ansible_base_cache: t.Optional[str] = None) -> str:
    """
    Create an ansible-base directory of the requested version.

    :arg aio_session: :obj:`aiohttp.client.ClientSession` to make http requests with.
    :arg ansible_base_version: Version of ansible-base to retrieve.
    :arg tmpdir: Temporary directory use as a scratch area for downloading to and the place that the
        ansible-base directory should be placed in.
    :kwarg ansible_base_cache: If given, a path to an Ansible-base checkout or expanded sdist.
        This will be used instead of downloading an ansible-base package if the version matches
        with ``ansible_base_version``.
    """
    if ansible_base_version == '@devel':
        # is the cache usable?
        if cache_is_devel(ansible_base_cache):
            assert ansible_base_cache is not None
            return ansible_base_cache

        install_file = await checkout_from_git(tmpdir)
    else:
        pypi_client = AnsibleBasePyPiClient(aio_session)
        if ansible_base_version == '@latest':
            ansible_base_version: pypiver.Version = await pypi_client.get_latest_version()
        else:
            ansible_base_version: pypiver.Version = pypiver.Version(ansible_base_version)

        # is the cache the asked for version?
        if cache_is_correct_version(ansible_base_cache, ansible_base_version):
            assert ansible_base_cache is not None
            return ansible_base_cache

        install_file = await pypi_client.retrieve(ansible_base_version, tmpdir)

    return install_file
