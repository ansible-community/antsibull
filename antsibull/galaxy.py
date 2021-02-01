# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functions to work with Galaxy."""

import os.path
import shutil
import typing as t
from urllib.parse import urljoin

import semantic_version as semver

from . import app_context
from .hashing import verify_hash
from .utils.http import retry_get

# The type checker can handle finding aiohttp.client but flake8 cannot :-(
if t.TYPE_CHECKING:
    import aiohttp.client


#: URL to galaxy. (Get the default from the context default)
_GALAXY_SERVER_URL = str(app_context.AppContext().galaxy_url)


class NoSuchCollection(Exception):
    """Collection name does not map to a collection on Galaxy."""


class NoSuchVersion(Exception):
    """Version does not match with any versions of a collection on Galaxy."""


class DownloadFailure(Exception):
    """Failure downloading a collection from Galaxy."""


class DownloadResults(t.NamedTuple):
    """Results of downloading a collection."""

    #: :obj:`semantic_version.Version` of the exact version of the collection that was downloaded.
    version: semver.Version
    #: Location on the filesystem of the downloaded collection.
    download_path: str


class GalaxyClient:
    """Class for querying the Galaxy REST API."""

    def __init__(self, aio_session: 'aiohttp.client.ClientSession',
                 galaxy_server: str = _GALAXY_SERVER_URL) -> None:
        """
        Create a GalaxyClient object to query the Galaxy Server.

        :arg aio_session: :obj:`aiohttp.ClientSession` with which to perform all
            requests to galaxy.
        :kwarg galaxy_server: URL to the galaxy server.
        """
        self.galaxy_server = galaxy_server
        self.aio_session = aio_session
        self.params = {'format': 'json'}

    async def _get_galaxy_versions(self, versions_url: str) -> t.List[str]:
        """
        Retrieve the complete list of versions for a collection from a galaxy endpoint.

        This internal function retrieves versions for collections from a Galaxy endpoint.  If the
        information is paged, it continues to retrieve linked pages until all of the information has
        been returned.

        :arg version_url: url to the page to retrieve.
        :returns: List of the all the versions of the collection.
        """
        params = self.params.copy()
        params['page_size'] = '100'
        async with retry_get(self.aio_session, versions_url, params=params,
                             acceptable_error_codes=[404]) as response:
            if response.status == 404:
                raise NoSuchCollection(f'No collection found at: {versions_url}')
            collection_info = await response.json()

        versions = []
        for version_record in collection_info['results']:
            versions.append(version_record['version'])

        if collection_info['next']:
            versions.extend(await self._get_galaxy_versions(collection_info['next']))

        return versions

    async def get_versions(self, collection: str) -> t.List[str]:
        """
        Retrieve all versions of a collection on Galaxy.

        :arg collection: Name of the collection to get version info for.
        :returns: List of all the versions of this collection on galaxy.
        """
        collection = collection.replace('.', '/')
        galaxy_url = urljoin(self.galaxy_server, f'api/v2/collections/{collection}/versions/')
        retval = await self._get_galaxy_versions(galaxy_url)
        return retval

    async def get_info(self, collection: str) -> t.Dict[str, t.Any]:
        """
        Retrieve information about the collection on Galaxy.

        :arg collection: Namespace.collection to retrieve information about.
        :returns: Dictionary of information about the collection.

        Please see the Galaxy REST API documentation for information on the structure of the
        returned data.

        .. seealso::
            An example return value from the
            `Galaxy REST API <https://galaxy.ansible.com/api/v2/collections/community/general/>`_
        """
        collection = collection.replace('.', '/')
        galaxy_url = urljoin(self.galaxy_server, f'api/v2/collections/{collection}/')

        async with retry_get(self.aio_session, galaxy_url, params=self.params,
                             acceptable_error_codes=[404]) as response:
            if response.status == 404:
                raise NoSuchCollection(f'No collection found at: {galaxy_url}')
            collection_info = await response.json()

        return collection_info

    async def get_release_info(self, collection: str,
                               version: t.Union[str, semver.Version]) -> t.Dict[str, t.Any]:
        """
        Retrive information about a specific version of a collection.

        :arg collection: Namespace.collection string naming the collection.
        :arg version: Version of the collection.
        :returns: Dictionary of information about the release.

        Please see the Galaxy REST API documentation for information on the structure of the
        returned data.

        .. seealso::
            An example return value from the
            `Galaxy REST API
            <https://galaxy.ansible.com/api/v2/collections/community/general/versions/0.1.1>`_
        """
        collection = collection.replace('.', '/')
        galaxy_url = urljoin(self.galaxy_server,
                             f'api/v2/collections/{collection}/versions/{version}/')

        async with retry_get(self.aio_session, galaxy_url, params=self.params,
                             acceptable_error_codes=[404]) as response:
            if response.status == 404:
                raise NoSuchCollection(f'No collection found at: {galaxy_url}')
            collection_info = await response.json()

        return collection_info

    async def get_latest_matching_version(self, collection: str,
                                          version_spec: str,
                                          pre: bool = False) -> semver.Version:
        """
        Get the latest version of a collection that matches a specification.

        :arg collection: Namespace.collection identifying a collection.
        :arg version_spec: String specifying the allowable versions.
        :kwarg pre: If True, allow prereleases (versions which have the form X.Y.Z.SOMETHING).
            This is **not** for excluding 0.Y.Z versions.  The default is False.
        :returns: :obj:`semantic_version.Version` of the latest collection version that satisfied
            the specification.

        .. seealso:: For the format of the version_spec, see the documentation
            of :obj:`semantic_version.SimpleSpec`
        """
        versions = await self.get_versions(collection)
        versions = [semver.Version(v) for v in versions]
        versions.sort(reverse=True)

        spec = semver.SimpleSpec(version_spec)
        for version in (v for v in versions if v in spec):
            # If we're excluding prereleases and this is a prerelease, then skip it.
            if not pre and version.prerelease:
                continue
            return version

        # No matching versions were found
        raise NoSuchVersion(f'{version_spec} did not match with any version of {collection}.')


class CollectionDownloader(GalaxyClient):
    """Manage downloading collections from Galaxy."""

    def __init__(self, aio_session: 'aiohttp.client.ClientSession',
                 download_dir: str,
                 galaxy_server: str = _GALAXY_SERVER_URL,
                 collection_cache: t.Optional[str] = None) -> None:
        """
        Create an object to download collections from galaxy.

        :arg aio_session: :obj:`aiohttp.ClientSession` with which to perform all
            requests to galaxy.
        :arg download_dir: Directory to download into.
        :kwarg galaxy_server: URL to the galaxy server.
        :kwarg collection_cache: If given, a path to a directory containing collection tarballs.
            These tarballs will be used instead of downloading new tarballs provided that the
            versions match the criteria (latest compatible version known to galaxy).
        """
        super().__init__(aio_session, galaxy_server)
        self.download_dir = download_dir
        # TODO: PY3.8: self.collection_cache: t.Final[t.Optional[str]] = collection_cache
        self.collection_cache = collection_cache

    async def download(self, collection: str, version: t.Union[str, semver.Version], ) -> str:
        """
        Download a collection.

        Downloads the collection at the specified version.

        :arg collection: Namespace.collection identifying the collection.
        :arg version: Version of the collection to download.
        :returns: The full path to the downloaded collection.
        """
        collection = collection.replace('.', '/')
        release_info = await self.get_release_info(collection, version)
        release_url = release_info['download_url']

        download_filename = os.path.join(self.download_dir, release_info['artifact']['filename'])
        sha256sum = release_info['artifact']['sha256']

        if self.collection_cache:
            if release_info['artifact']['filename'] in os.listdir(self.collection_cache):
                # TODO: PY3.8: We can use t.Final in __init__ instead of cast here.
                cached_copy = os.path.join(t.cast(str, self.collection_cache),
                                           release_info['artifact']['filename'])
                if await verify_hash(cached_copy, sha256sum):
                    shutil.copyfile(cached_copy, download_filename)
                return download_filename

        async with retry_get(self.aio_session, release_url,
                             acceptable_error_codes=[404]) as response:
            if response.status == 404:
                raise NoSuchCollection(f'No collection found at: {release_url}')

            with open(download_filename, 'wb') as f:
                lib_ctx = app_context.lib_ctx.get()
                # TODO: PY3.8: while chunk := await response.content.read(lib_ctx.chunksize):
                chunk = await response.content.read(lib_ctx.chunksize)
                while chunk:
                    f.write(chunk)
                    chunk = await response.content.read(lib_ctx.chunksize)

        # Verify the download
        if not await verify_hash(download_filename, sha256sum):
            raise DownloadFailure(f'{release_url} failed to download correctly.'
                                  f' Expected checksum: {sha256sum}')

        # Copy downloaded collection into cache
        if self.collection_cache:
            # TODO: PY3.8: We can use t.Final in __init__ instead of cast here.
            cached_copy = os.path.join(t.cast(str, self.collection_cache),
                                       release_info['artifact']['filename'])
            shutil.copyfile(download_filename, cached_copy)

        return download_filename

    async def download_latest_matching(self, collection: str,
                                       version_spec: str) -> DownloadResults:
        """
        Download the latest version of a collection that matches a specification.

        :arg collection: Namespace.collection identifying a collection.
        :arg version_spec: String specifying the allowable versions.
        :returns: :obj:`DownloadResults` with version and download path for the collection we
            downloaded.

        .. seealso:: For the format of the version_spec, see the documentation
            of :obj:`semantic_version.SimpleSpec`
        """
        version = await self.get_latest_matching_version(collection, version_spec)
        download_path = await self.download(collection, version)
        return DownloadResults(version=version, download_path=download_path)
