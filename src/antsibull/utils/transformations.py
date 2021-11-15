# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2021
"""General transformation functions."""

import typing as t
from collections import defaultdict


def get_collection_namespaces(collection_names: t.Iterable[str]) -> t.Dict[str, t.List[str]]:
    """
    Return the plugins which are in each collection.

    :arg collection_names: An iterable of collection names.
    :returns: Mapping from collection namespaces to list of collection names.
    """
    namespaces = defaultdict(list)
    for collection_name in collection_names:
        namespace, name = collection_name.split('.', 1)
        namespaces[namespace].append(name)
    return namespaces
