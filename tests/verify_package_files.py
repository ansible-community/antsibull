# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile
from collections.abc import Iterator, MutableMapping, Sequence
from pathlib import Path
from subprocess import run
from typing import Any, Union

import aiofiles
import aiohttp
from packaging.version import Version as PypiVer

from antsibull_build import build_ansible_commands
from antsibull_build.cli import antsibull_build
from antsibull_build.constants import MINIMUM_ANSIBLE_VERSIONS
from antsibull_build.utils.paths import temp_or_dir

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

DEFAULT_CACHE_DIR = HERE / ".cache"
DEFAULT_PACKAGE_DIR = HERE / "test_data" / "package-files"

PYPI_PATH = "https://files.pythonhosted.org/packages"
WHEEL_PATH = f"{PYPI_PATH}/py3/a/ansible/ansible-{{version}}-py3-none-any.whl"
SDIST_PATH = f"{PYPI_PATH}/source/a/ansible/ansible-{{version}}.tar.gz"

ANTSIBULL_BUILD = os.environ.get("ANTSIBULL_BUILD", "antsibull-build")
PLACEHOLDER_ANTSIBULL_VERSION = "(ANTSIBULL_VERSION)"


@dataclasses.dataclass
class AnsibleSdist:
    version: str
    dest_dir: Path

    @property
    def nv(self) -> str:
        return f"ansible-{self.version}"

    @property
    def name(self) -> Path:
        return Path(self.nv + ".tar.gz")

    @property
    def dest(self) -> Path:
        return self.dest_dir / self.name

    @property
    def url(self) -> str:
        return "/".join((PYPI_PATH, "source", "a", "ansible", str(self.name)))

    def extract_collections(self, extract_dir: Path) -> None:
        with tarfile.TarFile.open(self.dest) as file:
            collections_dir = str(Path(self.nv, "ansible_collections")) + "/"
            members: list[tarfile.TarInfo] = []
            for member in file.getmembers():
                if not member.name.startswith(collections_dir):
                    continue
                member.path = member.name[len(self.nv) + 1 :]
                members.append(member)
            file.extractall(extract_dir, members)

    def list_files(self) -> list[str]:
        with tarfile.TarFile.open(self.dest) as file:
            files: list[str] = []
            for info in file.getmembers():
                if info.isdir():
                    files.append(info.name + "/")
                else:
                    files.append(info.name)
            return sorted(files)


@dataclasses.dataclass
class AnsibleWheel:
    version: str
    dest_dir: Path

    @property
    def nv(self) -> str:
        return f"ansible-{self.version}"

    @property
    def name(self) -> Path:
        return Path(f"{self.nv}-py3-none-any.whl")

    @property
    def dest(self) -> Path:
        return self.dest_dir / self.name

    @property
    def url(self) -> str:
        return "/".join((PYPI_PATH, "py3", "a", "ansible", str(self.name)))

    def list_files(self) -> list[str]:
        with zipfile.ZipFile(self.dest) as file:
            files: list[str] = []
            for info in file.infolist():
                if info.is_dir():
                    files.append(info.filename + "/")
                else:
                    files.append(info.filename)
            return sorted(files)


DIST_TUPLE = tuple[Union[AnsibleSdist, AnsibleWheel], ...]


async def download_file(session: aiohttp.ClientSession, url: str, dest: Path) -> None:
    print(f"Downloading {url}...")
    async with session.get(url) as resp:
        async with aiofiles.open(dest, "wb") as fp:
            while chunk := await resp.content.read(4096):
                await fp.write(chunk)


def download_command(*, version: str, cache_dir: Path, force_dl: bool) -> None:
    async def dl() -> None:
        async with aiohttp.ClientSession() as session:
            dist = AnsibleSdist(version, cache_dir)
            if force_dl or not dist.dest.exists():
                await download_file(session, dist.url, dist.dest)

    asyncio.run(dl())


def generate_package_files(
    version: str,
    cached_dist: AnsibleSdist,
    extract_dir: Path,
    data_dir: Path,
    force_generate_setup_cfg: bool,
) -> None:
    cached_dist.extract_collections(extract_dir)
    cm = (
        patch_dict(MINIMUM_ANSIBLE_VERSIONS, "BUILD_META_MAKER", PypiVer(version))
        if force_generate_setup_cfg
        else contextlib.nullcontext()
    )
    cm2 = (
        patch_dict(MINIMUM_ANSIBLE_VERSIONS, "BUILD_META_NEW_URLS", PypiVer(version))
        if force_generate_setup_cfg
        else contextlib.nullcontext()
    )
    with (
        cm,
        cm2,
        patch_object(
            build_ansible_commands,
            "antsibull_version",
            PLACEHOLDER_ANTSIBULL_VERSION,
        ),
    ):
        if r := antsibull_build.run(
            [
                "antsibull-build",
                "generate-package-files",
                f"--data-dir={data_dir}",
                "--tags-file",
                f"--package-dir={extract_dir}",
                version,
            ]
        ):
            sys.exit(r)


@contextlib.contextmanager
def patch_dict(mapping: MutableMapping, key: Any, value: Any) -> Iterator[None]:
    old = mapping[key]
    try:
        mapping[key] = value
        yield
    finally:
        mapping[key] = old


@contextlib.contextmanager
def patch_object(object: Any, attr: str, new_value: Any) -> Iterator[None]:
    old_value = getattr(object, attr)
    try:
        setattr(object, attr, new_value)
        yield
    finally:
        setattr(object, attr, old_value)


def write_file_list(
    version: str, source_dir: Path, build_dir: Path | None = None
) -> DIST_TUPLE:
    with temp_or_dir(build_dir) as build_dir:
        run(
            [
                sys.executable,
                "-m",
                "build",
                f"--outdir={build_dir}",
                "--config-setting=--quiet",
                source_dir,
            ],
            check=True,
        )
        dists: DIST_TUPLE = (
            AnsibleSdist(version, Path(build_dir)),
            AnsibleWheel(version, Path(build_dir)),
        )
        dist_list_dir = source_dir / "dist-files"
        dist_list_dir.mkdir(exist_ok=True)
        for dist in dists:
            dist_list = dist_list_dir / f"{dist.name}.txt"
            dist_list.write_text("\n".join(dist.list_files()) + "\n")
        return dists


def check_command(
    *,
    version: str,
    package_dir: Path,
    cache_dir: Path,
    data_dir: Path,
    build_check: Path,
    build_dir: Path | None,
    force_generate_setup_cfg: bool,
) -> None:
    package_dir = package_dir / version
    cached_dist = AnsibleSdist(version, cache_dir)

    with temp_or_dir() as extract_dir:
        generate_package_files(
            version, cached_dist, extract_dir, data_dir, force_generate_setup_cfg
        )
        diff_args = ["-ur", "-x", "ansible_collections", "-x", "*egg-info"]
        if build_check:
            write_file_list(version, extract_dir, build_dir)
        else:
            diff_args.extend(("-x", "dist-files"))
        run(["diff", *diff_args, package_dir, extract_dir], check=True)

        # Make sure files can be regenerated
        generate_package_files(
            version, cached_dist, extract_dir, data_dir, force_generate_setup_cfg
        )
        run(["diff", *diff_args, package_dir, extract_dir], check=True)


def regen_command(
    *,
    version: str,
    package_dir: Path,
    cache_dir: Path,
    data_dir: Path,
    build_check: Path,
    clean: bool,
    build_dir: Path | None,
    force_generate_setup_cfg: bool,
) -> None:
    package_dir = package_dir / version
    cached_dist = AnsibleSdist(version, cache_dir)

    if clean:
        shutil.rmtree(package_dir, True)
    package_dir.mkdir(exist_ok=True)

    generate_package_files(
        version, cached_dist, package_dir, data_dir, force_generate_setup_cfg
    )
    if build_check:
        write_file_list(version, package_dir, build_dir)
    shutil.rmtree(package_dir / "ansible_collections", True)
    if egg_info := next(package_dir.glob("*.egg-info"), None):
        shutil.rmtree(egg_info, True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="action", dest="action", required=True)

    download_parser = subparsers.add_parser("download")
    download_parser.set_defaults(function=download_command)
    download_parser.add_argument("version")
    download_parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    download_parser.add_argument(
        "--force-dl", action=argparse.BooleanOptionalAction, default=False
    )

    _package_data_parser = argparse.ArgumentParser(add_help=False)
    _package_data_parser.add_argument("version")
    _package_data_parser.add_argument(
        "--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR
    )
    _package_data_parser.add_argument(
        "--cache-dir", type=Path, default=DEFAULT_CACHE_DIR
    )
    _package_data_parser.add_argument("--data-dir", type=Path, required=True)
    _package_data_parser.add_argument(
        "--build-check",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Default: true",
    )
    _package_data_parser.add_argument(
        "--build-dir",
        help="Directory to use for storing temporary build artifacts"
        " when --build-check is used",
        type=Path,
    )
    _package_data_parser.add_argument(
        "--force-generate-setup-cfg",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Generate setup.cfg even if that's not the default for VERSION."
        " Default: False",
    )

    check_parser = subparsers.add_parser("check", parents=[_package_data_parser])
    check_parser.set_defaults(function=check_command)

    regen_parser = subparsers.add_parser("regen", parents=[_package_data_parser])
    regen_parser.set_defaults(function=regen_command)
    regen_parser.add_argument(
        "--clean",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Default: false",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None):
    namespace = parse_args(argv)
    args = vars(namespace).copy()
    del args["action"]
    del args["function"]
    return namespace.function(**args)


if __name__ == "__main__":
    main()
