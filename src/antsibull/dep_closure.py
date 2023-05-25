# Author: Toshio Kuratomi <tkuratom@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2021
"""Check collection dependencies."""

from __future__ import annotations

import json
import pathlib
from collections import namedtuple
from collections.abc import Mapping

from antsibull_core import app_context
from semantic_version import SimpleSpec as SemVerSpec
from semantic_version import Version as SemVer

CollectionRecord = namedtuple("CollectionRecord", ("version", "dependencies"))


def parse_manifest(collection_dir: pathlib.Path) -> Mapping[str, CollectionRecord]:
    """Parse MANIFEST.json for a collection."""
    manifest = collection_dir.joinpath("MANIFEST.json")
    with manifest.open() as f:
        manifest_data = json.load(f)["collection_info"]

    collection_record = {
        f'{manifest_data["namespace"]}.{manifest_data["name"]}': CollectionRecord(
            manifest_data["version"], manifest_data["dependencies"]
        )
    }

    return collection_record


def analyze_deps(collections: Mapping[str, CollectionRecord]) -> list[str]:
    """Analyze dependencies of a set of collections. Return list of errors found."""
    errors = []

    # Look at dependencies
    # make sure their dependencies are found
    for collection_name, collection_info in collections.items():
        for dep_name, dep_version_spec in collection_info.dependencies.items():
            if dep_name not in collections:
                errors.append(
                    f"{collection_name} missing: {dep_name} ({dep_version_spec})"
                )
                continue

            dependency_version = SemVer(collections[dep_name].version)
            if dependency_version not in SemVerSpec(dep_version_spec):
                errors.append(
                    f"{collection_name} {collection_info.version} version_conflict:"
                    f" {dep_name}-{dependency_version} but needs"
                    f" {dep_version_spec}"
                )
                continue

    return errors


def check_collection_dependencies(collection_root: str) -> list[str]:
    """Analyze dependencies between collections in a collection root."""
    ansible_collection_dir = pathlib.Path(collection_root)
    errors = []

    collections: dict[str, CollectionRecord] = {}
    for namespace_dir in (n for n in ansible_collection_dir.iterdir() if n.is_dir()):
        for collection_dir in (c for c in namespace_dir.iterdir() if c.is_dir()):
            try:
                collections.update(parse_manifest(collection_dir))
            except FileNotFoundError:
                errors.append(f"{collection_dir} is not a valid collection")

    errors.extend(analyze_deps(collections))
    return errors


def validate_dependencies_command() -> int:
    """CLI functionality for analyzing dependencies."""
    app_ctx = app_context.app_ctx.get()

    collection_root: str = app_ctx.extra["collection_root"]

    errors = check_collection_dependencies(collection_root)

    for error in errors:
        print(error)

    return 3 if errors else 0
