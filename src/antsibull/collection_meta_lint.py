# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2024

"""
Classes to lint collection-meta.yaml
"""

from __future__ import annotations

import os

import pydantic as p
from antsibull_core import app_context
from antsibull_core.dependency_files import parse_pieces_file
from antsibull_core.yaml import load_yaml_file

from .collection_meta import CollectionMetadata, CollectionsMetadata, RemovalInformation


class _Validator:
    def __init__(self, *, all_collections: list[str], major_release: int):
        self.errors: list[str] = []
        self.all_collections = all_collections
        self.major_release = major_release

    def _validate_removal(
        self, collection: str, removal: RemovalInformation, prefix: str
    ) -> None:
        if removal.version != "TBD" and removal.version <= self.major_release:
            self.errors.append(
                f"{prefix} version: Removal version {removal.version} must"
                f" be larger than current major version {self.major_release}"
            )

        if (
            removal.announce_version is not None
            and removal.announce_version.major != self.major_release
        ):
            self.errors.append(
                f"{prefix} announce_version: Major version of {removal.announce_version}"
                f" must be the current major version {self.major_release}"
            )

        if removal.redirect_replacement_version is not None:
            if removal.redirect_replacement_version <= self.major_release:
                self.errors.append(
                    f"{prefix} redirect_replacement_version: Redirect removal version"
                    f" {removal.redirect_replacement_version} must be larger than"
                    f" current major version {self.major_release}"
                )
            if (
                removal.version != "TBD"
                and removal.redirect_replacement_version >= removal.version
            ):
                self.errors.append(
                    f"{prefix} redirect_replacement_version: Redirect removal version"
                    f" {removal.redirect_replacement_version} must be smaller than"
                    f" the removal major version {removal.version}"
                )

        if removal.reason == "renamed" and removal.new_name == collection:
            self.errors.append(
                f"{prefix} new_name: Must not be the collection's name"
            )

    def _validate_collection(
        self, collection: str, meta: CollectionMetadata, prefix: str
    ) -> None:
        if meta.repository is None:
            self.errors.append(f"{prefix} repository: Required field not provided")

        if meta.removal:
            self._validate_removal(collection, meta.removal, f"{prefix} removal ->")

    def validate(self, data: CollectionsMetadata) -> None:
        # Check order
        sorted_list = sorted(data.collections)
        raw_list = list(data.collections)
        if raw_list != sorted_list:
            for raw_entry, sorted_entry in zip(raw_list, sorted_list):
                if raw_entry != sorted_entry:
                    self.errors.append(
                        "The collection list must be sorted; "
                        f"{sorted_entry!r} must come before {raw_entry}"
                    )
                    break

        # Validate collection data
        remaining_collections = set(self.all_collections)
        for collection, meta in data.collections.items():
            if collection not in remaining_collections:
                self.errors.append(
                    f"collections -> {collection}: Collection not in ansible.in"
                )
            else:
                remaining_collections.remove(collection)
            self._validate_collection(
                collection, meta, f"collections -> {collection} ->"
            )

        # Complain about remaining collections
        for collection in sorted(remaining_collections):
            self.errors.append(f"collections: No metadata present for {collection}")


def lint_collection_meta() -> int:
    """Lint collection-meta.yaml."""
    app_ctx = app_context.app_ctx.get()

    major_release: int = app_ctx.extra["ansible_major_version"]
    data_dir: str = app_ctx.extra["data_dir"]
    pieces_file: str = app_ctx.extra["pieces_file"]

    validator = _Validator(
        all_collections=parse_pieces_file(os.path.join(data_dir, pieces_file)),
        major_release=major_release,
    )

    for cls in (
        # NOTE: The order is important here! The most deeply nested classes must come first,
        #       otherwise extra=forbid might not be used for something deeper in the hierarchy.
        RemovalInformation,
        CollectionMetadata,
        CollectionsMetadata,
    ):
        cls.model_config["extra"] = "forbid"
        cls.model_rebuild(force=True)

    collection_meta_path = os.path.join(data_dir, "collection-meta.yaml")
    if not os.path.exists(collection_meta_path):
        validator.errors.append(f"Cannot find {collection_meta_path}")
    else:
        data = load_yaml_file(collection_meta_path)
        try:
            parsed_data = CollectionsMetadata.parse_obj(data)
            validator.validate(parsed_data)
        except p.ValidationError as exc:
            for error in exc.errors():
                location = " -> ".join(str(loc) for loc in error["loc"])
                validator.errors.append(f'{location}: {error["msg"]}')

    for message in validator.errors:
        print(message)

    return 3 if validator.errors else 0
