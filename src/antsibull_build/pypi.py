# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Work with the PyPI API
"""

import datetime
from pathlib import Path
from typing import NamedTuple, Optional
from urllib.parse import urljoin

import aiohttp
import pydantic as p
from antsibull_core import app_context
from antsibull_fileutils.hashing import verify_hash

PYPI_BASE_URL = "https://pypi.org/pypi/"


class SdistAndWheelPair(NamedTuple):
    """
    Tuple of UrlInfo objects for a project's sdist and wheel
    """

    sdist: "UrlInfo"
    wheel: "UrlInfo"


class Release(p.BaseModel):
    """
    Model representing the response from the PyPI API releases endpoint.

    https://warehouse.pypa.io/api-reference/json.html#get--pypi--project_name---version--json
    """

    info: "ReleaseInfo"
    last_serial: int
    urls: list["UrlInfo"]
    vulnerabilities: list[dict]

    def get_sdist_and_wheel(self) -> SdistAndWheelPair:
        sdist: Optional[UrlInfo] = None
        wheel: Optional[UrlInfo] = None
        for release in self.urls:
            if not sdist and release.packagetype == "sdist":
                sdist = release
            elif not wheel and release.packagetype == "bdist_wheel":
                wheel = release
            else:
                break
            msg = f"Not {{}} was uploaded for {self.info.name}=={self.info.version}"
        if not sdist:
            raise ValueError(msg.format("sdist"))
        if not wheel:
            raise ValueError(msg.format("wheel"))
        return SdistAndWheelPair(sdist, wheel)


class ReleaseInfo(p.BaseModel):
    author: str
    author_email: str
    classifiers: list[str]
    description: str
    description_content_type: str
    docs_url: Optional[str]
    home_page: str
    keywords: Optional[str]
    license: str
    maintainer: Optional[str]
    maintainer_email: Optional[str]
    name: str
    package_url: str
    platform: Optional[str]
    project_url: str
    project_urls: dict[str, str]
    release_url: str
    requires_dist: list[str]
    requires_python: str
    summary: str
    version: str
    yanked: bool
    yanked_reason: Optional[str]


class UrlInfo(p.BaseModel):
    comment_text: str
    digests: dict[str, str]
    filename: str
    md5_digest: str
    packagetype: str
    python_version: str
    requires_python: Optional[str]
    size: int
    upload_time: datetime.datetime
    url: str
    yanked: bool
    yanked_reason: Optional[str]

    @property
    def sha256sum(self) -> str:
        return self.digests["sha256"]

    async def verify_local_file(self, file: Path) -> bool:
        """
        Check if a local file's name and sha256sum matches this release
        """
        if file.name != self.filename:
            return False
        lib_ctx = app_context.lib_ctx.get()
        return await verify_hash(file, self.sha256sum, chunksize=lib_ctx.chunksize)


# TODO pydantic v2+:
# + Release.model_rebuild
getattr(Release, "model_rebuild", getattr(Release, "update_forward_refs"))()


class PyPIClient:
    """
    Client for the PyPI Warehouse JSON API
    """

    def __init__(self, aio_session: aiohttp.ClientSession) -> None:
        self.aio_session = aio_session

    async def get_release(self, package: str, version: str) -> Release:
        url = urljoin(PYPI_BASE_URL, f"{package}/{version}/json")
        async with self.aio_session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return Release(**data)


__all__ = (
    "SdistAndWheelPair",
    "Release",
    "ReleaseInfo",
    "UrlInfo",
    "PyPIClient",
)
