# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2023
"""Handle version specific things."""

from __future__ import annotations

import asyncio
import os
import sys
import typing as t
from collections.abc import Mapping, Sequence

import aiohttp
import asyncio_pool  # type: ignore[import]
from antsibull_core import app_context
from antsibull_core.ansible_core import AnsibleCorePyPiClient
from antsibull_core.dependency_files import parse_pieces_file
from antsibull_core.galaxy import GalaxyClient, GalaxyContext
from packaging.version import Version as PypiVer
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


def load_constraints_if_exists(
    filename: str | os.PathLike[str],
) -> dict[str, SemVerSpec]:
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


def _display_exception(loop, context):  # pylint:disable=unused-argument
    print(context.get("exception"), file=sys.stderr)


async def get_version_info(
    collections: Sequence[str],
    pypi_server_url: str | None = None,
    *,
    galaxy_context: GalaxyContext,
) -> tuple[dict[str, t.Any], dict[str, list[str]]]:
    """
    Return the versions of all the collections and ansible-core
    """
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(_display_exception)

    requestors = {}
    lib_ctx = app_context.lib_ctx.get()
    async with (
        aiohttp.ClientSession(trust_env=True) as aio_session,
        asyncio_pool.AioPool(size=lib_ctx.thread_max) as pool,
    ):
        pypi_client = AnsibleCorePyPiClient(
            aio_session, pypi_server_url=pypi_server_url
        )
        requestors["_ansible_core"] = await pool.spawn(pypi_client.get_release_info())

        galaxy_client = GalaxyClient(aio_session, context=galaxy_context)
        for collection in collections:
            requestors[collection] = await pool.spawn(
                galaxy_client.get_versions(collection)
            )

        collections_to_versions = {}
        responses = await asyncio.gather(*requestors.values())

    ansible_core_release_infos: dict[str, t.Any] | None = None
    for idx, collection_name in enumerate(requestors):
        if collection_name == "_ansible_core":
            ansible_core_release_infos = responses[idx]
        else:
            collections_to_versions[collection_name] = responses[idx]

    if ansible_core_release_infos is None:
        raise RuntimeError("Internal error")

    return ansible_core_release_infos, collections_to_versions


def get_latest_ansible_core_version(
    ansible_core_versions: Sequence[str],
    ansible_core_version: PypiVer,
    pre: bool = False,
) -> PypiVer | None:
    """
    Retrieve the latest ansible-core bugfix release's version for the given ansible-core version.

    :arg ansible_core_versions: A list of ansible-core versions.
    :arg ansible_core_version: A ansible-core version.
    """
    versions = [PypiVer(v) for v in ansible_core_versions]
    next_version = PypiVer(
        f"{ansible_core_version.major}.{ansible_core_version.minor + 1}a"
    )
    newer_versions = [
        version
        for version in versions
        if ansible_core_version <= version < next_version
        and (pre or not version.is_prerelease)
    ]
    return max(newer_versions) if newer_versions else None


def get_latest_collection_version(
    versions: Sequence[str],
    collection: str,
    version_spec: str | None = None,
    pre: bool = False,
    prefer_pre: bool = False,
    constraint: SemVerSpec | None = None,
) -> SemVer:
    """
    Get the latest version of a collection that matches a specification.

    :arg versions: Sequence of collection versions
    :arg collection: Namespace.collection identifying a collection.
    :arg version_spec: Optional string specifying the allowable versions.
    :kwarg pre: If ``True``, allow prereleases (versions which have the form X.Y.Z.SOMETHING).
        This is **not** for excluding 0.Y.Z versions.  Non-pre-releases are still
        preferred over pre-releases, except if ``prefer_pre=True`` (for instance, with
        ``version_spec='>2.0.0-a1,<3.0.0'`` and ``pre=True``, if the available versions
        are 2.0.0-a1 and 2.0.0-a2, then 2.0.0-a2 will be returned.  If the available
        versions are 2.0.0 and 2.1.0-b2, 2.0.0 will be returned since non-pre-releases
        are preferred.) The default is ``False``.
    :kwarg prefer_pre: If ``True``, prefer newer pre-releases over stable releases. Is only
        used when ``pre=True``.
    :kwarg constraint: If provided, only consider versions that match this specification.
    :returns: :obj:`semantic_version.Version` of the latest collection version that satisfied
        the specification.

    .. seealso:: For the format of the version_spec, see the documentation
        of :obj:`semantic_version.SimpleSpec`
    """
    sem_versions = [SemVer(v) for v in versions]
    sem_versions.sort(reverse=True)

    if version_spec:
        spec = SemVerSpec(version_spec)
        sem_versions = [v for v in sem_versions if v in spec]

    if constraint:
        # Ignore all versions that do not match the constraints
        sem_versions = [v for v in sem_versions if v in constraint]

    prereleases = []
    for version in sem_versions:
        # If this is a pre-release, first check if there's a non-pre-release that
        # will satisfy the version_spec.
        if version.prerelease:
            # If we prefer prereleases, take this one.
            if pre and prefer_pre:
                return version
            prereleases.append(version)
            continue
        return version

    # We did not find a stable version that satisies the version_spec.  If we
    # allow prereleases, return the latest of those here.
    if pre and prereleases:
        return prereleases[0]

    # No matching versions were found
    constraint_clause = "" if constraint is None else f" (with constraint {constraint})"
    raise ValueError(
        f"{version_spec}{constraint_clause} did not match with any version of {collection}."
    )


def find_latest_compatible(
    ansible_core_version: PypiVer,  # pylint: disable=unused-argument
    collections_to_versions: Mapping[str, Sequence[str]],
    pre: bool = False,
    prefer_pre: bool = False,
    version_specs: Mapping[str, str] | None = None,
    constraints: Mapping[str, SemVerSpec] | None = None,
) -> dict[str, SemVer]:
    """
    Finds the latest compatible version of every collection from ``collections_to_versions``
    that matches the given ``vresion_specs`` and ``constraints``.

    ``pre`` and ``prefer_pre`` control whether pre-releases are acceptable (``pre=True``),
    and in case both matching pre-releases and releases are found, which ones to prefer
    (``prefer_pre=True`` prefers pre-releases over regular releases).
    """
    # Note: ansible-core compatibility is not currently implemented.  It will be a piece of
    # collection metadata that is present in the collection but may not be present in Galaxy.
    # We'll have to figure that out once the pieces are finalized

    version_specs = version_specs or {}
    constraints = constraints or {}

    reduced_versions = {}
    for dep, versions in collections_to_versions.items():
        reduced_versions[dep] = get_latest_collection_version(
            versions,
            dep,
            version_spec=version_specs.get(dep),
            pre=pre,
            prefer_pre=prefer_pre,
            constraint=constraints.get(dep),
        )

    return reduced_versions
