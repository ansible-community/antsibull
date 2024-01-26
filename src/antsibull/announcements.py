# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+
# (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Commands for generating release announcements
"""

from __future__ import annotations

import asyncio
import json
import sys
import webbrowser
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import lru_cache, partial
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING
from urllib.parse import quote as url_quote
from urllib.parse import urlencode, urljoin

import pydantic.json
import pyperclip  # type: ignore[import]
from aiohttp import ClientResponseError, ClientSession
from antsibull_core import app_context
from antsibull_core.dependency_files import DependencyFileData, DepsFile
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape
from packaging.version import Version as PypiVer
from typing_extensions import TypedDict

from antsibull.constants import ANSIBLE_FORUM_URL, BUILD_DATA_URL
from antsibull.pypi import PyPIClient, SdistAndWheelPair, UrlInfo

if TYPE_CHECKING:
    from _typeshed import StrOrBytesPath

ANNOUNCEMENTS = {
    "ansible-email-announcement.txt": "ansible-email-announcement.j2",
    "ansible-matrix-announcement.md": "ansible-matrix-announcement.j2",
}
SUBJECT = "Release announcement: Ansible community package {}"
MAIL_RECIPIENTS = (
    "ansible-devel@googlegroups.com",
    "ansible-project@googlegroups.com",
    "ansible-announce@googlegroups.com",
)
# pylint: disable-next=line-too-long
# https://meta.discourse.org/t/create-a-link-to-start-a-new-topic-with-pre-filled-information/28074 # noqa
FORUM_TAGS = ("release", "distro-packaging", "release-management")
FORUM_PARAMS: dict[str, str] = {
    "category": "news/releases",
    "tags": ",".join(FORUM_TAGS),
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


# pyre-ignore[13]: BaseModel initializes attributes when data is loaded
class AnnouncementsInfo(pydantic.BaseModel):
    """
    Represents the announcement files generated by `announcements_command`
    """

    template_vars: TemplateVars
    outputs: list[str]


def announcements_command() -> int:
    """
    Generate release announcements
    """
    app_ctx = app_context.app_ctx.get()
    ansible_version: str = app_ctx.extra["ansible_version"]
    output_dir: Path = app_ctx.extra["output_dir"]
    dist_dir: Path | None = app_ctx.extra["dist_dir"]
    send: bool = app_ctx.extra["send"]

    deps_filename = Path(app_ctx.extra["data_dir"], app_ctx.extra["deps_file"])
    deps_file = DepsFile(deps_filename)
    dependency_data = deps_file.parse()
    return asyncio.run(
        _announcements_command(
            ansible_version, output_dir, dist_dir, dependency_data, send
        )
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
        path.write_text(output + "\n")
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
    send: bool,
) -> int:
    if not (ctx := await get_data(ansible_version, dist_dir, dependency_data)):
        return 1
    for path in write_announcements(ANNOUNCEMENTS, ctx, output_dir):
        print("Wrote:", path)
    data = AnnouncementsInfo(template_vars=ctx, outputs=list(ANNOUNCEMENTS))
    info_path = output_dir / "announcements.json"
    write_announcements_json(data, info_path)
    print("Wrote:", info_path)
    if send and (rc := _send_announcements_command(output_dir, set(ACTIONS), True)):
        return rc
    return 0


def write_announcements_json(info: AnnouncementsInfo, file: StrOrBytesPath) -> None:
    with open(file, "w", encoding="utf-8") as fp:
        # pyre and pylint don't understand pydantic's __getattr__ magic
        # pyre-ignore[16] pylint: disable-next=no-member
        json.dump(info, fp, default=pydantic.json.pydantic_encoder, indent=2)


def load_announcements_json(file: StrOrBytesPath) -> AnnouncementsInfo:
    with open(file, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    return AnnouncementsInfo(**data)


@lru_cache
def get_body(directory: Path, name: str) -> str:
    return (directory / name).read_text()


def forum_announcement_webbrowser(
    directory: Path,
    info: AnnouncementsInfo,
    ctx: SendCtx,  # pylint: disable=unused-argument
) -> None:
    subject = SUBJECT.format(info.template_vars["version"])
    body = get_body(directory, "ansible-email-announcement.txt")
    params_dict = FORUM_PARAMS | {"title": subject, "body": body}
    params = "?" + urlencode(params_dict, quote_via=url_quote)
    url = urljoin(ANSIBLE_FORUM_URL, "new-topic") + params
    webbrowser.open(url)


def email_announcement_webbrowser(
    directory: Path,
    info: AnnouncementsInfo,
    ctx: SendCtx,  # pylint: disable=unused-argument
) -> None:
    subject = SUBJECT.format(info.template_vars["version"])
    body = get_body(directory, "ansible-email-announcement.txt")
    params_dict: dict[str, str] = {"subject": subject, "body": body}
    params = "?" + urlencode(params_dict, quote_via=url_quote)
    url = "mailto:" + ",".join(MAIL_RECIPIENTS) + params
    webbrowser.open(url)


def matrix_announcement(
    directory: Path,
    info: AnnouncementsInfo,  # pylint: disable=unused-argument
    ctx: SendCtx,
) -> None:
    body = get_body(directory, "ansible-matrix-announcement.md")
    try:
        forum_url = input("Enter the URL to the forum post: ")
    # Ctrl+D
    except EOFError:
        print("Continuing...")
        return
    body = body.replace("<FORUM LINK>", forum_url)
    message = dedent(
        """
    Please open your Matrix client and send the message to:
    - #community:ansible.com
    - #packaging:ansible.com
    - #social:ansible.com (mention @newsbot)
    """
    )
    if ctx.clipboard:
        pyperclip.copy(body)
        message += "\nThe message has been copied to your clipboard"
    else:
        message += "---\n" + body
    print(message)


ACTIONS: dict[str, Callable[[Path, AnnouncementsInfo, SendCtx], None]] = {
    "forum": forum_announcement_webbrowser,
    "email": email_announcement_webbrowser,
    "matrix": matrix_announcement,
}


@dataclass
class SendCtx:
    # Whether actions can write to the clipboard
    clipboard: bool


def send_announcements_command() -> int:
    """
    Interactively send announcements created by the `announcements` subcommand.
    """
    app_ctx = app_context.app_ctx.get()
    announcements_dir: Path = app_ctx.extra["announcements_dir"]
    actions: set[str] = set(app_ctx.extra["send_actions"])
    clipboard: bool = app_ctx.extra["clipboard"]

    return _send_announcements_command(announcements_dir, actions, clipboard)


def _send_announcements_command(
    announcements_dir: Path, actions: set[str], clipboard: bool
) -> int:
    info = load_announcements_json(announcements_dir / "announcements.json")
    send_ctx = SendCtx(clipboard)
    # Loop over ACTIONS this way to make sure that order is preserved.
    # For example, we want the Matrix announcement to happen last
    for action, func in ACTIONS.items():
        if action not in actions:
            continue
        print(f"Handling {action}...")
        func(announcements_dir, info, send_ctx)

    return 0
