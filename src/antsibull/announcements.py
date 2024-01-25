# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Commands for generating release announcements
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from typing import TypedDict

from aiohttp import ClientResponseError, ClientSession
from antsibull_core import app_context
from antsibull_core.dependency_files import DependencyFileData, DepsFile
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape
from packaging.version import Version as PypiVer

from antsibull.constants import BUILD_DATA_URL
from antsibull.pypi import PyPIClient, SdistAndWheelPair, UrlInfo

ANNOUNCEMENTS = {
    "ansible-email-announcement.txt": "ansible-email-announcement.j2",
    "ansible-matrix-announcement.md": "ansible-matrix-announcement.j2",
}

eprint = partial(print, file=sys.stderr)

jinja_env = Environment(
    loader=PackageLoader(__package__, "data"),
    autoescape=select_autoescape(),
    trim_blocks=True,
    undefined=StrictUndefined,
)


def email_heading(content):
    """
    Given a string, convert it into an email heading
    """
    return content + "\n" + "-" * len(content)


jinja_env.filters["email_heading"] = email_heading


class TemplateVars(TypedDict):
    """
    Variables used in the Jinja2 template
    """

    version: str
    major_version: int
    core_version: str
    core_major_version: str
    build_data_path: str
    release_tarball: UrlInfo
    release_wheel: UrlInfo


def announcements_command() -> int:
    """
    Generate release announcements
    """
    app_ctx = app_context.app_ctx.get()
    ansible_version: str = app_ctx.extra["ansible_version"]
    output_dir: Path = app_ctx.extra["output_dir"]
    dist_dir: Path | None = app_ctx.extra["dist_dir"]

    deps_filename = Path(app_ctx.extra["data_dir"], app_ctx.extra["deps_file"])
    deps_file = DepsFile(deps_filename)
    dependency_data = deps_file.parse()
    return asyncio.run(
        _announcements_command(ansible_version, output_dir, dist_dir, dependency_data)
    )


async def verify_dists(dists: SdistAndWheelPair, dist_dir: Path) -> str | None:
    for dist in dists:
        dist_path = dist_dir / dist.filename
        if not await asyncio.to_thread(dist_path.is_file):
            return f"{dist_path.name} was not found in --dist-dir"
        if not await dist.verify_local_file(dist_path):
            return f"{dist_path} differs from {dist.url}"
    return None


def write_announcements(
    announcements: dict[str, str], ctx: TemplateVars, output_dir: Path
) -> Iterator[Path]:
    for name, template in announcements.items():
        output = jinja_env.get_template(template).render(**ctx)
        path = output_dir.joinpath(name)
        path.write_text(output)
        yield path


async def get_data(
    ansible_version: str, dist_dir: Path | None, dependency_data: DependencyFileData
) -> TemplateVars | None:
    async with ClientSession() as aio_session:
        client = PyPIClient(aio_session)
        try:
            release = await client.get_release("ansible", ansible_version)
        except ClientResponseError as exc:
            eprint(f"Failed to retrieve data for ansible=={ansible_version}: {exc}")
            return None
        try:
            dists = release.get_sdist_and_wheel()
        except ValueError as exc:
            eprint(exc)
            return None
        if dist_dir and (err := await verify_dists(dists, dist_dir)):
            eprint(err)
            return None

        version = dependency_data.ansible_version
        major_version = PypiVer(dependency_data.ansible_version).major
        core_version = dependency_data.ansible_core_version
        core_version_obj = PypiVer(dependency_data.ansible_core_version)
        core_major_version = f"{core_version_obj.major}.{core_version_obj.minor}"
        build_data_path = f"{BUILD_DATA_URL}/blob/{version}/{major_version}"
        ctx = TemplateVars(
            version=version,
            major_version=major_version,
            core_version=core_version,
            core_major_version=core_major_version,
            build_data_path=build_data_path,
            release_tarball=dists.sdist,
            release_wheel=dists.wheel,
        )
        return ctx


async def _announcements_command(
    ansible_version: str,
    output_dir: Path,
    dist_dir: Path | None,
    dependency_data: DependencyFileData,
) -> int:
    if not (ctx := await get_data(ansible_version, dist_dir, dependency_data)):
        return 1
    for path in write_announcements(ANNOUNCEMENTS, ctx, output_dir):
        print("Wrote:", path)
    return 0
