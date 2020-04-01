# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Functions to work with Galaxy
"""

import hashlib
import os.path
from urllib.parse import urljoin

import semantic_version as semver


CHUNKSIZE = 4096


class NoSuchCollection(Exception):
    pass

class DownloadFailure(Exception):
    pass


class GalaxyClient:
    def __init__(self, galaxy_server, aio_session):
        self.galaxy_server = galaxy_server
        self.aio_session = aio_session
        self.params = {'format': 'json'}

    async def _get_galaxy_versions(self, galaxy_url):
        async with self.aio_session.get(galaxy_url, params=self.params) as response:
            if response.status == 404:
                raise NoSuchCollection(f'No collection found at: {galaxy_url}')
            collection_info = await response.json()

        versions = []
        for version_record in collection_info['results']:
            versions.append(version_record['version'])

        if collection_info['next']:
            versions.extend(await self._get_galaxy_versions(collection_info['next']))

        return versions

    async def get_versions(self, collection):
        collection = collection.replace('.', '/')
        galaxy_url = urljoin(self.galaxy_server, f'api/v2/collections/{collection}/versions/')
        retval = await self._get_galaxy_versions(galaxy_url)
        return retval

    async def get_info(self, collection):
        collection = collection.replace('.', '/')
        galaxy_url = urljoin(self.galaxy_server, f'api/v2/collections/{collection}/')

        async with self.aio_session.get(galaxy_url, params=self.params) as response:
            if response.status == 404:
                raise NoSuchCollection(f'No collection found at: {galaxy_url}')
            collection_info = await response.json()

        return collection_info

    async def get_release_info(self, collection, version):
        collection = collection.replace('.', '/')
        galaxy_url = urljoin(self.galaxy_server,
                             f'api/v2/collections/{collection}/versions/{version}/')

        async with self.aio_session.get(galaxy_url, params=self.params) as response:
            if response.status == 404:
                raise NoSuchCollection(f'No collection found at: {galaxy_url}')
            collection_info = await response.json()

        return collection_info

    async def get_release(self, collection, version, dest_dir):
        collection = collection.replace('.', '/')
        release_info = await self.get_release_info(collection, version)
        release_url = release_info['download_url']

        download_filename = os.path.join(dest_dir, release_info['artifact']['filename'])
        sha256sum = release_info['artifact']['sha256']

        async with self.aio_session.get(release_url) as response:
            if response.status == 404:
                raise NoSuchCollection(f'No collection found at: {release_url}')

            with open(download_filename, 'wb') as f:
                while chunk := await response.content.read(CHUNKSIZE):
                    f.write(chunk)

        # Verify the download
        hasher = hashlib.sha256()
        with open(download_filename, 'rb') as f:
            while chunk := f.read(CHUNKSIZE):
                hasher.update(chunk)
        if hasher.hexdigest() != sha256sum:
            raise DownloadFailure(f'{release_url} failed to download correctly.  Failed checksum:\n'
                                  f'Expected: {sha256sum}\n'
                                  f'Actual:   {hasher.hexdigest()}')


class CollectionDownloader:
    def __init__(self, galaxy_server, aio_session, download_dir):
        self.galaxy_client = GalaxyClient(galaxy_server, aio_session)
        self.download_dir = download_dir

    async def _get_latest_matching_version(self, collection, version_spec):
        versions = await self.galaxy_client.get_versions(collection)
        versions = [semver.Version(v) for v in versions]
        versions.sort(reverse=True)

        spec = semver.SimpleSpec(version_spec)
        for version in (v for v in versions if v in spec):
            return version

        # No matching versions were found
        return None

    async def retrieve(self, collection, version_spec, dest_dir):
        version = await self._get_latest_matching_version(collection, version_spec)
        await self.galaxy_client.get_release(collection, version, dest_dir)
        return version
