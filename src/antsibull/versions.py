# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2023
"""Handle version specific things."""

from __future__ import annotations

import os

from antsibull_core.dependency_files import parse_pieces_file
from semantic_version import SimpleSpec as SemVerSpec
from semantic_version import Version as SemVer


class _FeatureFreezeVersion:
    """
    Helper for making semantic version range specification valid for feature freeze.
    """

    def __init__(self, spec: str, collection_name: str):
        self.potential_clauses: list = []
        self.spec = spec
        self.collection_name = collection_name
        self.upper_operator: str | None = None
        self.upper_version: SemVer | None = None
        self.min_version: SemVer | None = None
        self.pinned = False

        spec_obj = SemVerSpec(spec)

        # If there is a single clause, it's available as spec_obj.clause;
        # multiple ones are available as spec_obj.clause.clauses.
        try:
            clauses = spec_obj.clause.clauses
        except AttributeError:
            clauses = [spec_obj.clause]

        self.clauses = clauses
        for clause in clauses:
            self._process_clause(clause)

    def _process_clause(self, clause) -> None:
        """
        Process one clause of the version range specification.
        """
        if clause.operator in ("<", "<="):
            if self.upper_operator is not None:
                raise ValueError(
                    f"Multiple upper version limits specified for {self.collection_name}:"
                    f" {self.spec}"
                )
            self.upper_operator = clause.operator
            self.upper_version = clause.target
            # Omit the upper bound as we're replacing it
            return

        if clause.operator == ">=":
            # Save the lower bound so we can write out a new compatible version
            if self.min_version is not None:
                raise ValueError(
                    f"Multiple minimum versions specified for {self.collection_name}: {self.spec}"
                )
            self.min_version = clause.target

        if clause.operator == ">":
            raise ValueError(
                f"Strict lower bound specified for {self.collection_name}: {self.spec}"
            )

        if clause.operator == "==":
            self.pinned = True

        self.potential_clauses.append(clause)

    def compute_new_spec(self) -> str:
        """
        Compute a new version range specification that only allows newer patch releases that also
        match the original range specification.
        """
        if self.pinned:
            if len(self.clauses) > 1:
                raise ValueError(
                    f"Pin combined with other clauses for {self.collection_name}: {self.spec}"
                )
            return self.spec

        upper_operator = self.upper_operator
        upper_version = self.upper_version
        if upper_operator is None or upper_version is None:
            raise ValueError(
                f"No upper version limit specified for {self.collection_name}: {self.spec}"
            )

        min_version = self.min_version
        if min_version is None:
            raise ValueError(
                f"No minimum version specified for {self.collection_name}: {self.spec}"
            )

        if min_version.next_minor() <= upper_version:
            upper_operator = "<"
            upper_version = min_version.next_minor()

        new_clauses = sorted(
            str(clause)
            for clause in self.potential_clauses
            if clause.target < upper_version
        )
        new_clauses.append(f"{upper_operator}{upper_version}")
        return ",".join(new_clauses)


def feature_freeze_version(spec: str, collection_name: str) -> str:
    """
    Make semantic version range specification valid for feature freeze.
    """
    return _FeatureFreezeVersion(spec, collection_name).compute_new_spec()


def load_constraints_if_exists(filename: str) -> dict[str, SemVerSpec]:
    """
    Load a constraints file, if it exists.
    """
    result: dict[str, SemVerSpec] = {}
    if not os.path.exists(filename):
        return result
    for line in parse_pieces_file(filename):
        record = [entry.strip() for entry in line.split(":", 1)]
        if len(record) < 2:
            raise ValueError(
                f'While parsing {filename}: record "{line}" is not of the form "collection: spec"'
            )
        collection = record[0]
        try:
            constraint = SemVerSpec(record[1])
        except ValueError as exc:
            raise ValueError(
                f"While parsing {filename}: cannot parse constraint"
                f' "{record[1]}" for collection {collection}: {exc}'
            ) from exc
        result[collection] = constraint
    return result
