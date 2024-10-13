# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)


"""
Utilities to run sanity tests accross collections
"""

from __future__ import annotations

import datetime
import json
import shlex
import shutil
import sys
from collections.abc import Collection, Iterable, Iterator, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from subprocess import CompletedProcess
from typing import TYPE_CHECKING, Any, TypedDict

from antsibull_core import app_context
from antsibull_core.logging import log
from antsibull_core.subprocess_util import log_run
from antsibull_fileutils.yaml import store_yaml_file
from packaging.version import Version

from antsibull_build.constants import SANITY_TESTS_BANNED_IGNORES, SANITY_TESTS_DEFAULT
from antsibull_build.types import CollectionName, add_dataclass_yaml_type

if TYPE_CHECKING:
    from _typeshed import StrPath

mlog = log.fields(mod=__name__)


class SanityOutput(TypedDict):
    """
    Mapping of `ansible-test sanity` output and other related data
    """

    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str
    runtime: float
    test_json: dict[str, Any]
    ignore_entries: list[IgnoreEntry]
    banned_ignore_entries: list[IgnoreEntry]
    ignores_file: str | None


class CollectionOutput(TypedDict):
    """
    Collection entry
    """

    failed: bool
    sanity: SanityOutput


class EnvDetails(TypedDict):
    """
    Details about the ansible-test environment
    """

    ansible_test_version: str
    sanity_tests: list[str]


class Output(TypedDict):
    """
    Parent mapping of the sanity test data file
    """

    collections: dict[CollectionName, CollectionOutput]
    total_runtime: float
    env_details: EnvDetails


@dataclass(frozen=True)
class IgnoreEntry:
    """
    Represents an entry in an `ansible-test sanity` ignores file
    """

    file: str
    test: str
    remainder: str

    def as_str(self) -> str:
        return f"{self.file} {self.test}{self.remainder}"


add_dataclass_yaml_type(IgnoreEntry)


def parse_ignores_file(file: StrPath) -> Iterator[IgnoreEntry]:
    """
    Parse a sanity test ignore file
    """
    flog = mlog.fields(func="parse_sanity_test_file", file=file)
    with open(file, encoding="utf-8") as fp:
        for line in fp:
            line = line.rstrip("\n")
            parsed = line.split(" ", 2)
            if len(parsed) == 2:
                parsed.append("")
            if len(parsed) != 3:
                flog.error("Failed to parse line: {0}", line)
                continue
            yield IgnoreEntry(file=parsed[0], test=parsed[1], remainder=parsed[2])


def get_ignores_file(directory: Path, version: str) -> Path | None:
    """
    Determine the path to a sanity test ignore file for a certain ansible-test `version`

    Args:
        directory:
            Collection's directory
        version:
            Version of ansible-test

    Returns:
        Path to a sanity test ignore file if one exists or `None`
    """
    expected = directory / "tests/sanity" / f"ignore-{version}.txt"
    return expected if expected.is_file() else None


def filter_invalid_ignores(
    entries: Iterable[IgnoreEntry],
    matches: Collection[str] = SANITY_TESTS_BANNED_IGNORES,
) -> Iterator[IgnoreEntry]:
    """
    Given an Iterable of `IgnoreEntry`s, filter out entries that match `matches`

    Args:
        matches:
            Iterable of `IgnoreEntry`s
        invalid:
            `Collection` of sanity test ignore names
    Yields:
        `IgnoreEntry`s that match `matches`
    """
    for entry in entries:
        if entry.test in matches:
            yield entry


def is_git_repo(base_directory: Path, directory: Path) -> bool:
    """
    Check if a collection directory is its own git directory

    Args:
        base_directory:
            Base directory that contains the collection directory
        directory:
            Collection directory

    Returns:
        Whether or not the collection directory is its own git directory
    """
    repo = log_run(["git", "rev-parse", "--git-dir"], check=False, cwd=directory)
    if repo.returncode == 128:
        return False
    git_directory = Path(repo.stdout.strip())
    if not git_directory.is_absolute():
        git_directory = directory.resolve() / git_directory
    # If the collection base directory is a subdirectory of the git repository,
    # we need to create an empty one for the collection.
    return not base_directory.resolve().is_relative_to(git_directory.parent)


def create_stub_git_repo(directory: StrPath) -> None:
    """
    Create a git repository and initial commit with all files in a directory
    """
    git_run = partial(log_run, cwd=directory)
    git_run(["git", "init", "."])
    git_run(["git", "add", "."])
    git_run(["git", "commit", "--no-gpg-sign", "-m", "init"])


def remove_test_output_files(directory: Path) -> None:
    """
    Clean ansible-test output directory
    """
    if (output := directory / "tests" / "output").exists():
        shutil.rmtree(output)


def get_errors(directory: Path) -> dict[str, Any]:
    """
    Get `ansible-test sanity` error JSON output
    """
    files = directory.glob("tests/output/bot/ansible-test-sanity-*.json")
    data: dict[str, Any] = {}
    for file in files:
        with file.open() as fp:
            data[file.name] = json.load(fp)
    return data


def get_ansible_test_version(ansible_test_bin: Sequence[StrPath]) -> str:
    """
    Get the ansible-test version from `ansible_test_bin`
    """
    args = [*ansible_test_bin, "--version"]
    stdout = log_run(args).stdout.strip()
    version = stdout.split(" ")[-1]
    # Ensure version is parsable
    Version(version)
    return version


def run_sanity_tests(
    collection: CollectionName,
    directory: Path,
    tests: Sequence[str],
    quiet: bool,
    ansible_test_bin: Sequence[StrPath] = ("ansible-test",),
) -> tuple[CompletedProcess, float]:
    """
    Run `ansible-test sanity` and log
    """
    test_args = [f"--test={test}" for test in tests]
    args = [
        *ansible_test_bin,
        "sanity",
        *test_args,
        "--docker",
        "--lint",
    ]
    print(f"* Running: {args} for {collection}", file=sys.stderr)

    now = datetime.datetime.now()
    cmd = log_run(
        args,
        # Always show stderr
        stderr_loglevel="debug" if quiet else "error",
        cwd=directory,
        check=False,
    )
    after = datetime.datetime.now()
    total = after - now
    runtime = total.seconds / 60
    failed = "FAILURE: " if cmd.returncode else ""
    print(f"* {failed}Finished in {runtime:.2f} minutes\n", file=sys.stderr)
    return cmd, runtime


def _get_ignores_info(
    directory: Path, ansible_test_version: str
) -> tuple[list[IgnoreEntry], list[IgnoreEntry], str | None]:
    v = Version(ansible_test_version)
    ignore_file = get_ignores_file(directory, f"{v.major}.{v.minor}")
    ignores: list[IgnoreEntry] = []
    banned_ignores: list[IgnoreEntry] = []
    file_base: str | None = None
    if ignore_file:
        ignores = list(parse_ignores_file(ignore_file))
        banned_ignores = list(filter_invalid_ignores(ignores))
        file_base = str(ignore_file.relative_to(directory))
    return ignores, banned_ignores, file_base


def handle_collection(
    directory: Path,
    tests: Sequence[str],
    clean: bool,
    quiet: bool,
    env_details: EnvDetails,
    ansible_test_bin: Sequence[StrPath] = ("ansible-test",),
) -> tuple[CollectionName, CollectionOutput]:
    """
    Run the tests for a collection
    """
    collection = CollectionName.from_galaxy_yml(directory / "galaxy.yml")
    if clean:
        remove_test_output_files(directory)
    if not is_git_repo(directory.parent, directory):
        create_stub_git_repo(directory)
    cmd, runtime = run_sanity_tests(
        collection, directory, tests, quiet, ansible_test_bin
    )
    errors = get_errors(directory)
    ignores, banned_ignores, ignores_file = _get_ignores_info(
        directory, env_details["ansible_test_version"]
    )
    sanity_output = SanityOutput(
        cmd=cmd.args,
        returncode=cmd.returncode,
        stdout=cmd.stdout,
        stderr=cmd.stderr,
        runtime=runtime,
        test_json=errors,
        ignore_entries=ignores,
        banned_ignore_entries=banned_ignores,
        ignores_file=ignores_file,
    )
    return (
        collection,
        # Namespace the data under "sanity" for futureproofing
        {
            "sanity": sanity_output,
            "failed": bool(cmd.returncode) or bool(banned_ignores),
        },
    )


def get_percentage(collections: dict[CollectionName, CollectionOutput]) -> str:
    """
    Determine success/failure percentage
    """
    colls_succeeded = [cdata for cdata in collections.values() if not cdata["failed"]]
    perc = f"{len(colls_succeeded)/len(collections)*100:.2f}%"
    frac = f"{len(colls_succeeded)} / {len(collections)}"
    return f"{perc} ({frac}) succeeded"


def sanity_tests_command() -> int:
    """
    Run sanity tests across multiple collections and store results
    """
    app_ctx = app_context.app_ctx.get()
    collections: list[Path] = app_ctx.extra["collection_paths"]
    tests: list[str] = app_ctx.extra["tests"] or list(SANITY_TESTS_DEFAULT)
    clean: bool = app_ctx.extra["clean"]
    quiet: bool = app_ctx.extra["quiet"]
    error_output: Path = app_ctx.extra["error_output"]
    # Allow spaces for something like "python -m ansible test"
    ansible_test_bin: list[str] = shlex.split(app_ctx.extra["ansible_test_bin"])

    env_details: EnvDetails = {
        "ansible_test_version": get_ansible_test_version(ansible_test_bin),
        "sanity_tests": tests,
    }

    collections_errors: dict[CollectionName, CollectionOutput] = dict(
        handle_collection(
            collection, tests, clean, quiet, env_details, ansible_test_bin
        )
        for collection in collections
    )
    total_runtime = sum(
        cerrors["sanity"]["runtime"] for cerrors in collections_errors.values()
    )
    data: Output = {
        "collections": collections_errors,
        "total_runtime": total_runtime,
        "env_details": env_details,
    }

    print(get_percentage(collections_errors), f"in {total_runtime:.2f} minutes!")
    store_yaml_file(error_output, data)
    return 0 if any(c["failed"] for c in collections_errors.values()) else 1
