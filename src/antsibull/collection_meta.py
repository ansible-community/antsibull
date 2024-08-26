# Author: Felix Fontein <felix@fontein.de>
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020

"""
Classes to encapsulate collection metadata from collection-meta.yaml
"""

from __future__ import annotations

import os
import typing as t

import pydantic as p
from antsibull_fileutils.yaml import load_yaml_file
from packaging.version import Version as PypiVer
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated


def _convert_pypi_version(v: t.Any) -> t.Any:
    if not isinstance(v, str):
        raise ValueError(f"must be a string, got {v!r}")
    if not v:
        raise ValueError(f"must be a non-trivial string, got {v!r}")
    version = PypiVer(v)
    if len(version.release) != 3:
        raise ValueError(
            f"must be a version with three release numbers (e.g. 1.2.3, 2.3.4a1), got {v!r}"
        )
    return version


PydanticPypiVersion = Annotated[PypiVer, BeforeValidator(_convert_pypi_version)]


class RemovalInformation(p.BaseModel):
    """
    Stores metadata on when and why a collection will get removed.
    """

    model_config = p.ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    version: t.Union[int, t.Literal["TBD"]]
    reason: t.Literal["deprecated", "considered-unmaintained", "renamed"]
    announce_version: t.Optional[PydanticPypiVersion] = None
    new_name: t.Optional[str] = None
    discussion: t.Optional[p.HttpUrl] = None
    redirect_replacement_version: t.Optional[int] = None


class CollectionMetadata(p.BaseModel):
    """
    Stores metadata about one collection.
    """

    model_config = p.ConfigDict(extra="ignore")

    changelog_url: t.Optional[str] = p.Field(alias="changelog-url", default=None)
    collection_directory: t.Optional[str] = p.Field(
        alias="collection-directory", default=None
    )
    repository: t.Optional[str] = None
    tag_version_regex: t.Optional[str] = None
    maintainers: list[str] = []
    removal: t.Optional[RemovalInformation] = None


class CollectionsMetadata(p.BaseModel):
    """
    Stores metadata about a set of collections.
    """

    model_config = p.ConfigDict(extra="ignore")

    collections: dict[str, CollectionMetadata]

    @staticmethod
    def load_from(deps_dir: str | None):
        if deps_dir is None:
            return CollectionsMetadata(collections={})
        collection_meta_path = os.path.join(deps_dir, "collection-meta.yaml")
        if not os.path.exists(collection_meta_path):
            return CollectionsMetadata(collections={})
        data = load_yaml_file(collection_meta_path)
        return CollectionsMetadata.parse_obj(data)

    def get_meta(self, collection_name: str) -> CollectionMetadata:
        result = self.collections.get(collection_name)
        if result is None:
            result = CollectionMetadata()
            self.collections[collection_name] = result
        return result
