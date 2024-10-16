# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Misc. utility functions for the `from_source` package
"""


from __future__ import annotations

from collections.abc import Sequence
from fnmatch import fnmatch

from semantic_version import Version as SemVer

from antsibull_build.tagging import CollectionTagData
from antsibull_build.types import CollectionName


def filter_tag_data(
    collections: dict[CollectionName, CollectionTagData],
    globs: Sequence[str] | None = None,
) -> dict[CollectionName, CollectionTagData]:
    return {
        collection: data
        for collection, data in collections.items()
        if globs is None or any(fnmatch(collection, glob) for glob in globs)
    }


def tag_data_as_version_mapping(
    collections: dict[CollectionName, CollectionTagData]
) -> dict[CollectionName, SemVer]:
    """
    Convert a collection: CollectionTagData mapping to a collection: version mapping
    """
    return {
        collection: SemVer(data["version"]) for collection, data in collections.items()
    }


__all__ = ("filter_tag_data", "tag_data_as_version_mapping")
