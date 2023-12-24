# Author: Toshio Kuratomi <tkuratom@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020
"""Build command for creating a new major Ansible version."""

from __future__ import annotations

import asyncio
import os

from antsibull_core import app_context
from antsibull_core.dependency_files import BuildFile, parse_pieces_file
from packaging.version import Version as PypiVer

from .changelog import ChangelogData
from .utils.galaxy import create_galaxy_context
from .versions import (
    find_latest_compatible,
    get_version_info,
    load_constraints_if_exists,
)


def new_ansible_command() -> int:
    app_ctx = app_context.app_ctx.get()
    lib_ctx = app_context.lib_ctx.get()
    collections = parse_pieces_file(
        os.path.join(app_ctx.extra["data_dir"], app_ctx.extra["pieces_file"])
    )
    galaxy_context = asyncio.run(create_galaxy_context())
    ansible_core_release_infos, collections_to_versions = asyncio.run(
        get_version_info(
            collections, str(lib_ctx.pypi_url), galaxy_context=galaxy_context
        )
    )
    ansible_core_versions = [
        (PypiVer(version), data[0]["requires_python"])
        for version, data in ansible_core_release_infos.items()
    ]
    ansible_core_versions.sort(reverse=True, key=lambda ver_req: ver_req[0])

    constraints_filename = os.path.join(
        app_ctx.extra["data_dir"], app_ctx.extra["constraints_file"]
    )
    constraints = load_constraints_if_exists(constraints_filename)

    ansible_core_version, python_requires = ansible_core_versions[0]
    dependencies = find_latest_compatible(
        ansible_core_version,
        collections_to_versions,
        pre=app_ctx.extra["allow_prereleases"],
        prefer_pre=True,
        constraints=constraints,
    )

    build_filename = os.path.join(
        app_ctx.extra["dest_data_dir"], app_ctx.extra["build_file"]
    )
    build_file = BuildFile(build_filename)
    build_file.write(
        app_ctx.extra["ansible_version"],
        str(ansible_core_version),
        dependencies,
        python_requires=python_requires,
    )

    changelog = ChangelogData.ansible(app_ctx.extra["dest_data_dir"])
    changelog.changes.save()

    return 0
