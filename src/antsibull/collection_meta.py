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

import typing as t
import os
from collections.abc import Mapping

from antsibull_core.yaml import load_yaml_file


class CollectionMetadata:
    '''
    Stores metadata about one collection.
    '''

    changelog_url: str | None
    collection_directory: str | None
    repository: str | None
    tag_version_regex: str | None

    def __init__(self, source: Mapping[str, t.Any] | None = None):
        if source is None:
            source = {}
        self.changelog_url = source.get('changelog-url')
        self.collection_directory = source.get('collection-directory')
        self.repository = source.get('repository')
        self.tag_version_regex = source.get('tag_version_regex')


class CollectionsMetadata:
    '''
    Stores metadata about a set of collections.
    '''

    data: dict[str, CollectionMetadata]

    def __init__(self, deps_dir: str | None):
        self.data = {}
        if deps_dir is not None:
            collection_meta_path = os.path.join(deps_dir, 'collection-meta.yaml')
            if os.path.exists(collection_meta_path):
                data = load_yaml_file(collection_meta_path)
                if data and 'collections' in data:
                    for collection_name, collection_data in data['collections'].items():
                        self.data[collection_name] = CollectionMetadata(collection_data)

    def get_meta(self, collection_name: str) -> CollectionMetadata:
        result = self.data.get(collection_name)
        if result is None:
            result = CollectionMetadata()
            self.data[collection_name] = result
        return result
