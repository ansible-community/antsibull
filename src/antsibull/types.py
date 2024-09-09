# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Types used in the antsibull codebase
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar

import yaml
from antsibull_fileutils.yaml import load_yaml_file

if TYPE_CHECKING:
    from _typeshed import StrPath

_T = TypeVar("_T")


class CollectionName(str):
    """
    String subclass that represents a collection with a NAMESPACE.NAME
    """

    __slots__ = ("__namespace", "__name")

    def __init__(self, *args, **kwargs) -> None:  # pylint: disable=unused-argument
        namespace, _, name = self.partition(".")
        if not namespace or not name:
            raise ValueError(f"{self!r} is not a valid collection name")
        # str should be immutable. Make these private and expose via `@property`s.
        self.__namespace = namespace
        self.__name = name

    @property
    def namespace(self) -> str:
        """
        Collection namespace
        """
        return self.__namespace

    @property
    def name(self) -> str:
        """
        Collection name
        """
        return self.__name

    @property
    def parts(self) -> tuple[str, str]:
        """
        Returns a tuple of (self.namespace, self.name)
        """
        return self.namespace, self.name

    @classmethod
    def from_pair(cls, namespace: str, name: str) -> CollectionName:
        """
        Construct a `CollectionName` object from a `namespace` and `name`
        """
        return cls(".".join((namespace, name)))

    @classmethod
    def from_galaxy_yml(cls, path: StrPath) -> CollectionName:
        """
        Construct a `CollectionName` object from a `galaxy.yml` file
        """
        data = load_yaml_file(path)
        return cls.from_pair(data["namespace"], data["name"])

    def __hash__(self) -> int:
        return hash(type(self)) + super().__hash__()


def add_yaml_type(
    typ: type[_T],
    converter: Callable[[_T], Any] = str,
    representer_parent: Callable = yaml.representer.SafeRepresenter.represent_str,
) -> None:
    """
    Add a type to the YAML serializer. Defaults to serializing as a string.
    """
    dumpers: list[type[Any]] = [yaml.SafeDumper]
    try:
        cdumper = yaml.CSafeDumper
    except AttributeError:
        pass
    else:
        dumpers.append(cdumper)

    def representer(rep: Any, obj: Any) -> Any:
        return representer_parent(rep, converter(obj))

    for dumper in dumpers:
        dumper.add_representer(typ, representer)


add_dataclass_yaml_type = partial(
    add_yaml_type,
    converter=dataclasses.asdict,
    representer_parent=lambda dumper, data: yaml.representer.SafeRepresenter.represent_mapping(
        dumper, "tag:yaml.org,2002:map", data
    ),
)


add_yaml_type(CollectionName)


def make_collection_mapping(mapping: dict[str, _T]) -> dict[CollectionName, _T]:
    """
    Convert `str` keys in a mapping to `CollectionName` objects
    """
    return {CollectionName(collection): value for collection, value in mapping.items()}


__all__ = (
    "CollectionName",
    "add_yaml_type",
    "add_dataclass_yaml_type",
    "make_collection_mapping",
)
