# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Code for generating Python build configuration for ansible
"""

from __future__ import annotations

import copy
import os
from collections import defaultdict
from collections.abc import Collection, Iterator
from configparser import ConfigParser
from email import message_from_file
from email.message import Message
from pathlib import Path
from typing import Any, Union

from antsibull_core.dependency_files import DependencyFileData
from jinja2 import Template
from packaging.version import Version as PypiVer

from .constants import (
    ANSIBLE_FORUM_URL,
    BUILD_DATA_URL,
    COLLECTION_EXCLUDE_DIRS,
    DOCSITE_BASE_URL,
    DOCSITE_COMMUNITY_URL,
    MINIMUM_ANSIBLE_VERSIONS,
)
from .utils.get_pkg_data import get_antsibull_data


class IniType:
    """
    Python collections with custom __str__ methods that
    can be serialized as INI
    """

    def _i_iter_lines(self) -> Iterator[str]:
        raise NotImplementedError

    def __str__(self) -> str:
        return "\n".join(self._i_iter_lines())


class IniDict(IniType, dict):
    def _i_iter_lines(self) -> Iterator[str]:
        yield ""
        for key, value in self.items():
            if key == "":
                yield f"={value}"
            else:
                yield f"{key} = {value}"


class IniList(IniType, list):
    def _i_iter_lines(self) -> Iterator[str]:
        yield ""
        for value in self:
            yield f"  {value}"


INI_TYPES = Union[IniType, str, bool]

OLD_URLS = IniDict(
    {
        "Bug Tracker": "https://github.com/ansible/ansible/issues",
        "Code of Conduct": DOCSITE_COMMUNITY_URL + "/code_of_conduct.html",
        "Documentation": DOCSITE_BASE_URL,
        "Mailing lists": DOCSITE_COMMUNITY_URL
        + "/communication.html#mailing-list-information",
        "Source Code": "https://github.com/ansible/ansible",
    }
)

NEW_URLS = IniDict(
    {
        "Build Data": BUILD_DATA_URL,
        "Code of Conduct": DOCSITE_COMMUNITY_URL + "/code_of_conduct.html",
        "Documentation": DOCSITE_BASE_URL,
        "Forum": ANSIBLE_FORUM_URL,
    }
)

DEFAULT_METADATA: dict[str, INI_TYPES] = {
    "name": "ansible",
    "description": "Radically simple IT automation",
    "long_description": "file: README.rst",
    "long_description_content_type": "text/x-rst",
    "author": "Ansible, Inc.",
    "author_email": "info@ansible.com",
    "url": "https://ansible.com/",
    "license": "GPL-3.0-or-later",
    "classifiers": IniList(
        [
            "Development Status :: 5 - Production/Stable",
            "Environment :: Console",
            "Framework :: Ansible",
            "Intended Audience :: Developers",
            "Intended Audience :: Information Technology",
            "Intended Audience :: System Administrators",
            "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
            "Natural Language :: English",
            "Operating System :: POSIX",
        ]
    ),
}

DEFAULT_OPTIONS: dict[str, INI_TYPES] = {"zip_safe": False}
DEFAULT_ENTRY_POINTS: dict[str, INI_TYPES] = {
    "console_scripts": IniDict(
        {"ansible-community": "ansible_collections.ansible_community:main"}
    )
}

DEFAULT_CONFIG: dict[str, dict[str, INI_TYPES]] = {
    "metadata": DEFAULT_METADATA,
    "options": DEFAULT_OPTIONS,
    "options.entry_points": DEFAULT_ENTRY_POINTS,
}


def _get_collection_data(collection_path: Path) -> list[str]:
    directories = []
    for root, dirs, _ in os.walk(collection_path, topdown=True, followlinks=True):
        if root == str(collection_path):
            # Make sure that all directories starting with '.', and all
            # directories called 'tests' or 'docs', are not traversed into.
            for dirname in list(dirs):
                if dirname in COLLECTION_EXCLUDE_DIRS or dirname.startswith("."):
                    dirs.remove(dirname)
            continue
        relative_dir = str(Path(root).relative_to(collection_path))
        directories.append(relative_dir)
    return sorted(directories)


def _get_exclude_package_data(
    collection_names: Collection[str], collection_root: Path
) -> Iterator[str]:
    for collection in collection_names:
        relpath = Path(collection.replace(".", "/"))
        path = collection_root / relpath
        for directory in COLLECTION_EXCLUDE_DIRS:
            if path.joinpath(directory).is_dir():
                yield str(relpath / directory / "*")
        if any(file.name.startswith(".") for file in path.iterdir()):
            yield str(relpath / ".*")


class BuildMetaMaker:
    """
    Generate a setup.cfg and other Python metadata for ansible
    """

    package_dir: Path
    collections_dir: Path
    ansible_version: PypiVer
    dependency_data: DependencyFileData
    ansible_core_version: PypiVer
    ansible_core_checkout: Path
    python_requires: str | None

    config: defaultdict[str, dict[str, INI_TYPES]]
    ansible_core_metadata: Message
    _collection_directories: dict[str, list[str]]

    def __init__(
        self,
        *,
        package_dir: str | os.PathLike[str],
        collections_dir: str | os.PathLike[str] | None = None,
        ansible_version: PypiVer,
        dependency_data: DependencyFileData,
        ansible_core_version: PypiVer,
        ansible_core_checkout: str | os.PathLike[str],
        initial_config: dict[str, dict[str, INI_TYPES]] | None = None,
        python_requires: str | None,
    ) -> None:
        self.package_dir = Path(package_dir)
        if collections_dir:
            self.collections_dir = Path(collections_dir)
        else:
            self.collections_dir = self.package_dir / "ansible_collections"
        self.ansible_version = ansible_version
        self.dependency_data = dependency_data
        self.ansible_core_version = ansible_core_version
        self.ansible_core_checkout = Path(ansible_core_checkout)
        initial_config = copy.deepcopy(initial_config or DEFAULT_CONFIG)
        self.config = defaultdict(dict, initial_config)
        self.python_requires = python_requires

        with (self.ansible_core_checkout / "PKG-INFO").open(encoding="utf-8") as fp:
            self.ansible_core_metadata = message_from_file(fp)

        self._generated = False
        # TODO: Remove once we drop LegacyBuildMetaMaker
        self._collection_directories: dict[str, str] = {}

    def __getitem__(self, key: str) -> Any:
        return self.config[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.config[key] = value

    @property
    def core_python_requires(self) -> str:
        result = self.ansible_core_metadata.get("Requires-Python")
        if not result:
            raise ValueError("ansible-core's metadata is missing 'Requires-Python'")
        return result

    @property
    def core_python_classifiers(self) -> list[str]:
        result = self.ansible_core_metadata.get_all("Classifier")
        if not result:
            raise ValueError("ansible-core's metadata is missing Classifiers")
        return [
            classifier
            for classifier in result
            if classifier.startswith("Programming Language :: Python ::")
        ]

    def add_collection_ignores(self) -> None:
        if self.ansible_version >= MINIMUM_ANSIBLE_VERSIONS["PACKAGE_DATA_NEW_METHOD"]:
            self._package_data_new_method()
        else:
            self._package_data_old_method()

    def _package_data_new_method(self) -> None:
        collection_namespaces: dict[str, list[str]] = defaultdict(list)
        # We only need this as an attribute for the LegacyBuildMetaMaker compat
        # TODO: Remove once we drop LegacyBuildMetaMaker
        collection_directories = self._collection_directories
        for collection in self.dependency_data.deps:
            namespace, name = collection.split(".", 1)
            collection_namespaces[namespace].append(name)
            collection_path = self.collections_dir / namespace / name
            collection_directories[collection] = _get_collection_data(collection_path)

        self["options"]["package_dir"] = IniDict({"": "."})
        self["options"]["packages"] = "find_namespace:"

        self["options.packages.find"]["include"] = IniList(
            ["ansible_collections", "ansible_collections.*"]
        )
        self["options.packages.find"]["exclude"] = IniList()
        excludes = self["options.packages.find"]["exclude"]

        for collection in sorted(self.dependency_data.deps):
            excludes.extend(
                (
                    f"ansible_collections.{collection}.tests",
                    f"ansible_collections.{collection}.tests.*",
                    f"ansible_collections.{collection}.docs",
                    f"ansible_collections.{collection}.docs.*",
                )
            )
            data = self["options.package_data"][f"ansible_collections.{collection}"] = (
                IniList()
            )

            data.append("*")
            for directory in collection_directories[collection]:
                data.extend([f"{directory}/*", f"{directory}/.*"])

    def _package_data_old_method(self) -> None:
        self["options"]["packages"] = IniList(["ansible_collections"])
        self["options"]["include_package_data"] = True
        self["options.exclude_package_data"]["ansible_collections"] = IniList(
            _get_exclude_package_data(self.dependency_data.deps, self.collections_dir)
        )

    def generate(self) -> None:
        self["metadata"]["version"] = self.ansible_version
        self["metadata"].setdefault("classifiers", IniList()).extend(
            self.core_python_classifiers
        )
        self["metadata"].setdefault(
            "project_urls",
            (
                NEW_URLS
                if self.ansible_version
                >= MINIMUM_ANSIBLE_VERSIONS["BUILD_META_NEW_URLS"]
                else OLD_URLS
            ),
        )
        self["options"].setdefault("install_requires", IniList()).append(
            f"ansible-core ~= {self.ansible_core_version}"
        )

        self["options"]["python_requires"] = (
            self.python_requires or self.core_python_requires
        )

        self.add_collection_ignores()

        self._generated = True

    def write(self, file: Path | None = None) -> None:
        if not self._generated:
            self.generate()
        parser = ConfigParser()
        parser.read_dict(self.config)
        file = file or self.package_dir.joinpath("setup.cfg")
        with file.open("w", encoding="utf-8") as fp:
            parser.write(fp)


class LegacyBuildMetaMaker:
    """
    Generate a setup.py and other Python metadata for ansible.
    This is a wrapper around `BuildMetaMaker`.
    """

    def __init__(
        self,
        *,
        package_dir: str | os.PathLike[str],
        collections_dir: str | os.PathLike[str] | None = None,
        ansible_version: PypiVer,
        dependency_data: DependencyFileData,
        ansible_core_version: PypiVer,
        ansible_core_checkout: str | os.PathLike[str],
        python_requires: str | None,
    ) -> None:
        self.maker: BuildMetaMaker = BuildMetaMaker(
            package_dir=package_dir,
            collections_dir=collections_dir,
            ansible_version=ansible_version,
            dependency_data=dependency_data,
            ansible_core_version=ansible_core_version,
            ansible_core_checkout=ansible_core_checkout,
            initial_config=DEFAULT_CONFIG,
            python_requires=python_requires,
        )

    def write(self, file: Path | None = None) -> None:
        file = file or self.maker.package_dir / "setup.py"

        self.maker.generate()

        collection_exclude_paths = self.maker["options.exclude_package_data"].get(
            "ansible_collections", []
        )

        setup_tmpl = Template(get_antsibull_data("ansible-setup_py.j2").decode("utf-8"))
        setup_contents = setup_tmpl.render(
            version=self.maker.ansible_version,
            ansible_core_package_name="ansible-core",
            ansible_core_version=self.maker.ansible_core_version,
            collection_deps="",
            # not PACKAGE_DATA_NEW_METHOD
            collection_exclude_paths=sorted(collection_exclude_paths),
            # PACKAGE_DATA_NEW_METHOD
            collection_names=sorted(self.maker.dependency_data.deps),
            # pylint: disable-next=protected-access
            collection_directories=self.maker._collection_directories,
            #
            python_requires=self.maker["options"]["python_requires"],
            PypiVer=PypiVer,
        )
        file.write_text(setup_contents, encoding="utf-8")
