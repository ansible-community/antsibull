# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functions for working with the ansible-base package."""
import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Union
from urllib.parse import urljoin

import aiofiles
import packaging.version as pypiver
import sh

from .compat import best_get_loop

if TYPE_CHECKING:
    import aiohttp.client


#: URL to checkout ansible-base from.
ANSIBLE_BASE_URL = 'https://github.com/ansible/ansible'
#: URL to pypi.
PYPI_SERVER_URL = 'https://test.pypi.org/'
#: Number of bytes to read or write in one chunk
CHUNKSIZE = 4096


class UnknownVersion(Exception):
    """Raised when a requested version does not exist."""


@lru_cache
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

    @lru_cache
    async def get_info(self) -> Dict[str, Any]:
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

    async def get_versions(self) -> List[pypiver.Version]:
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

    async def retrieve(self, ansible_base_version: Union[str, pypiver.Version],
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


async def create_sdist(dist_dir):
    # TODO: Should we move code that does this into here?
    pass


async def get_ansible_base(aio_session: 'aiohttp.client.ClientSession',
                           ansible_base_version: str,
                           tmpdir: str) -> str:
    """
    Create an ansible-base directory of the requested version.

    :arg aio_session: :obj:`aiohttp.client.ClientSession` to make http requests with.
    :arg ansible_base_version: Version of ansible-base to retrieve.
    :arg tmpdir: Temporary directory use as a scratch area for downloading to and the place that the
        ansible-base directory should be placed in.
    """
    if ansible_base_version == '@devel':
        install_dir = await checkout_from_git(tmpdir)
        install_file = await create_sdist(install_dir)
    else:
        pypi_client = AnsibleBasePyPiClient(aio_session)
        if ansible_base_version == '@latest':
            ansible_base_version: pypiver.Version = await pypi_client.get_latest_version()
        install_file = await pypi_client.retrieve(ansible_base_version, tmpdir)

    return install_file
