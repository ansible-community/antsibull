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
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from subprocess import CompletedProcess
from typing import TYPE_CHECKING, Any, TypedDict

from antsibull_core import app_context
from antsibull_core.subprocess_util import log_run
from antsibull_core.yaml import store_yaml_file
from packaging.version import Version

from antsibull.constants import SANITY_TESTS_DEFAULT
from antsibull.types import CollectionName

if TYPE_CHECKING:
    from _typeshed import StrPath


class SanityOutput(TypedDict):
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str
    runtime: float
    test_json: dict[str, Any]


class CollectionOutput(TypedDict):
    failed: bool
    sanity: SanityOutput


class EnvDetails(TypedDict):
    ansible_test_version: str
    sanity_tests: list[str]


class Output(TypedDict):
    collections: dict[CollectionName, CollectionOutput]
    total_runtime: float
    env_details: EnvDetails


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


def handle_collection(
    directory: Path,
    tests: Sequence[str],
    clean: bool,
    quiet: bool,
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
    sanity_output = SanityOutput(
        cmd=cmd.args,
        returncode=cmd.returncode,
        stdout=cmd.stdout,
        stderr=cmd.stderr,
        runtime=runtime,
        test_json=errors,
    )
    return (
        collection,
        # Namespace the data under "sanity" for futureproofing
        {"sanity": sanity_output, "failed": bool(cmd.returncode)},
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
        handle_collection(collection, tests, clean, quiet, ansible_test_bin)
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
