# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import annotations

import pytest

from antsibull_build.types import CollectionName, make_collection_mapping


def test_collection_name() -> None:
    collection_obj = CollectionName("community.general")
    assert (
        (collection_obj.namespace, collection_obj.name)
        == ("community", "general")
        == collection_obj.parts
    )
    hash(collection_obj)


@pytest.mark.parametrize(
    "collection,error_msg",
    [
        pytest.param("abc.", "'abc.' is not a valid collection name"),
        pytest.param(".abc", "'.abc' is not a valid collection name"),
    ],
)
def test_collection_name_error(collection: str, error_msg: str) -> None:
    with pytest.raises(ValueError, match=error_msg):
        CollectionName(collection)


def test_make_collection_mapping() -> None:
    mapping = {"abc.abc": 1, "xyz.xyz": 1}
    expected = {CollectionName("abc.abc"): 1, CollectionName("xyz.xyz"): 1}
    assert make_collection_mapping(mapping) == expected
