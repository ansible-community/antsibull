# Author: Toshio Kuratomi <tkuratom@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020
"""Entrypoint to the antsibull-build tool."""

from __future__ import annotations

import argparse
import os.path
import sys
from pathlib import Path

import twiggy  # type: ignore[import]
from antsibull_core.logging import initialize_app_logging, log
from packaging.version import Version as PypiVer

initialize_app_logging()

# We have to call initialize_app_logging() before these imports so that the log object is configured
# correctly before other antisbull modules make copies of it.
# pylint: disable=wrong-import-position,ungrouped-imports
from antsibull_core import app_context  # noqa: E402
from antsibull_core.args import (  # noqa: E402
    InvalidArgumentError,
    get_toplevel_parser,
    normalize_toplevel_options,
)
from antsibull_core.config import ConfigError, load_config  # noqa: E402
from antsibull_core.vendored._argparse_booleanoptionalaction import (  # noqa: E402
    BooleanOptionalAction,
)

from ..announcements import ACTIONS as ALLOWED_SEND_ACTIONS  # noqa: E402
from ..announcements import (  # noqa: E402
    announcements_command,
    send_announcements_command,
)
from ..build_ansible_commands import (  # noqa: E402
    build_single_command,
    generate_package_files_command,
    prepare_command,
    rebuild_single_command,
)
from ..build_changelog import build_changelog  # noqa: E402
from ..constants import MINIMUM_ANSIBLE_VERSION, SANITY_TESTS_DEFAULT  # noqa: E402
from ..dep_closure import validate_dependencies_command  # noqa: E402
from ..from_source import verify_upstream_command  # noqa: E402
from ..from_source.verify import LENIENT_FILE_ERROR_IGNORES, FileError  # noqa: E402
from ..new_ansible import new_ansible_command  # noqa: E402
from ..sanity_tests import sanity_tests_command  # noqa: E402
from ..tagging import validate_tags_command, validate_tags_file_command  # noqa: E402

# pylint: enable=wrong-import-position


mlog = log.fields(mod=__name__)

DEFAULT_FILE_BASE = "ansible"
DEFAULT_PIECES_FILE = f"{DEFAULT_FILE_BASE}.in"

ARGS_MAP = {
    "new-ansible": new_ansible_command,
    "prepare": prepare_command,
    "single": build_single_command,
    "changelog": build_changelog,
    "rebuild-single": rebuild_single_command,
    "validate-deps": validate_dependencies_command,
    "validate-tags": validate_tags_command,
    "validate-tags-file": validate_tags_file_command,
    "generate-package-files": generate_package_files_command,
    "verify-upstreams": verify_upstream_command,
    "sanity-tests": sanity_tests_command,
    "announcements": announcements_command,
    "send-announcements": send_announcements_command,
}
DISABLE_VERIFY_UPSTREAMS_IGNORES_SENTINEL = "NONE"
DEFAULT_ANNOUNCEMENTS_DIR = Path("build/announce")


def _normalize_commands(
    args: argparse.Namespace,  # pylint: disable=unused-argument
) -> None:
    # If command names change and old ones need to be deprecated, do that here.
    # Check out the git history for examples.
    pass


def _normalize_build_options(args: argparse.Namespace) -> None:
    if args.command in (
        "validate-deps",
        "validate-tags-file",
        "verify-upstreams",
        "sanity-tests",
        "send-announcements",
    ):
        return

    if args.ansible_version < MINIMUM_ANSIBLE_VERSION:
        raise InvalidArgumentError(
            f"Ansible < {MINIMUM_ANSIBLE_VERSION} is not supported"
            " by this antsibull version."
        )

    if not os.path.isdir(args.data_dir):
        raise InvalidArgumentError(f"{args.data_dir} must be an existing directory")


def _normalize_build_write_data_options(args: argparse.Namespace) -> None:
    if args.command not in (
        "new-ansible",
        "prepare",
        "single",
        "rebuild-single",
        "changelog",
    ):
        return

    if args.dest_data_dir is None:
        args.dest_data_dir = args.data_dir

    if not os.path.isdir(args.dest_data_dir):
        raise InvalidArgumentError(
            f"{args.dest_data_dir} must be an existing directory"
        )


def _normalize_new_release_options(args: argparse.Namespace) -> None:
    if args.command != "new-ansible":
        return

    if args.pieces_file is None:
        args.pieces_file = DEFAULT_PIECES_FILE

    pieces_path = os.path.join(args.data_dir, args.pieces_file)
    if not os.path.isfile(pieces_path):
        raise InvalidArgumentError(
            f"The pieces file, {pieces_path}, must already"
            " exist. It should contain one namespace.collection"
            " per line"
        )

    compat_version_part = f"{args.ansible_version.major}"

    if args.build_file is None:
        basename = os.path.basename(os.path.splitext(args.pieces_file)[0])
        args.build_file = f"{basename}-{compat_version_part}.build"

    if args.constraints_file is None:
        basename = os.path.basename(os.path.splitext(args.pieces_file)[0])
        args.constraints_file = f"{basename}-{compat_version_part}.constraints"


def _check_release_build_directories(args: argparse.Namespace) -> None:
    if args.command in ("single", "rebuild-single"):
        if not os.path.isdir(args.sdist_dir):
            raise InvalidArgumentError(
                f"{args.sdist_dir} must be an existing directory"
            )

    if args.command in ("rebuild-single",):
        if args.sdist_src_dir is not None and os.path.exists(args.sdist_src_dir):
            raise InvalidArgumentError(f"{args.sdist_src_dir} must not exist")


def _normalize_release_build_options(args: argparse.Namespace) -> None:  # noqa: C901
    deps_file_only: tuple[str, ...] = ("announcements",)
    if args.command not in (
        "prepare",
        "single",
        "rebuild-single",
        "generate-package-files",
        *deps_file_only,
    ):
        return

    compat_version_part = f"{args.ansible_version.major}"

    if args.build_file is None:
        args.build_file = DEFAULT_FILE_BASE + f"-{compat_version_part}.build"

    build_filename = os.path.join(args.data_dir, args.build_file)
    if args.command not in deps_file_only and not os.path.isfile(build_filename):
        raise InvalidArgumentError(
            f"The build file, {build_filename} must already exist."
            " It should contains one namespace.collection and range"
            " of versions per line"
        )

    if args.constraints_file is None:
        basename = os.path.basename(os.path.splitext(args.build_file)[0])
        args.constraints_file = f"{basename}.constraints"

    if args.deps_file is None:
        version_suffix = f"-{compat_version_part}"
        basename = os.path.basename(os.path.splitext(args.build_file)[0])
        if basename.endswith(version_suffix):
            basename = basename[: -len(version_suffix)]

        args.deps_file = f"{basename}-{args.ansible_version}.deps"

    if args.command in deps_file_only:
        return

    if args.tags_file:
        _check_tags_file(args)

    if args.command in ("prepare", "single") and args.galaxy_file is None:
        version_suffix = f"-{compat_version_part}"
        basename = os.path.basename(os.path.splitext(args.build_file)[0])
        if basename.endswith(version_suffix):
            basename = basename[: -len(version_suffix)]

        args.galaxy_file = f"{basename}-{args.ansible_version}.yaml"

    _check_release_build_directories(args)


def _check_tags_file(args: argparse.Namespace) -> None:
    if args.tags_file == "DEFAULT":
        args.tags_file = f"{DEFAULT_FILE_BASE}-{args.ansible_version}-tags.yaml"
    tags_path = os.path.join(args.data_dir, args.tags_file)

    if args.command == "rebuild-single" and not os.path.isfile(tags_path):
        raise InvalidArgumentError(f"{tags_path} does not exist!")


def _normalize_release_rebuild_options(args: argparse.Namespace) -> None:
    if args.command not in ("rebuild-single", "validate-tags"):
        return

    deps_filename = os.path.join(args.data_dir, args.deps_file)
    if not os.path.isfile(deps_filename):
        raise InvalidArgumentError(
            f"The dependency file, {deps_filename} must already exist."
        )


def _normalize_validate_tags_options(args: argparse.Namespace) -> None:
    if args.command not in ("validate-tags",):
        return
    if args.deps_file is None:
        args.deps_file = DEFAULT_FILE_BASE + f"-{args.ansible_version}.deps"


def _normalize_validate_tags_file_options(args: argparse.Namespace) -> None:
    if args.command not in ("validate-tags-file", "validate-upstreams"):
        return
    if not os.path.exists(args.tags_file):
        raise InvalidArgumentError(f"{args.tags_file} does not exist!")


def _normalize_generate_package_files_options(args: argparse.Namespace) -> None:
    if args.command not in ("generate-package-files",):
        return
    if not os.path.isdir(args.package_dir):
        raise InvalidArgumentError(f"{args.package_dir} does not exist!")

    args.collections_dir = args.collections_dir or os.path.join(
        args.package_dir, "ansible_collections"
    )
    if not os.path.isdir(args.collections_dir):
        raise InvalidArgumentError(f"{args.collections_dir} does not exist!")


def _normalize_verify_upstream_options(args: argparse.Namespace) -> None:
    if args.command not in ("verify-upstreams",):
        return
    if all((args.tree_dir, args.checkouts_dir)):
        tree_dir: Path = args.tree_dir
        checkouts_dir: Path = args.checkouts_dir
        if tree_dir.resolve() == checkouts_dir.resolve():
            raise InvalidArgumentError(
                "--tree-dir and --checkouts-dir must be unique values"
            )
    for arg, value in {
        "--tree-dir": args.tree_dir,
        "--checkouts-dir": args.checkouts_dir,
    }.items():
        if not value:
            continue
        if (directory := value / "ansible_collections").exists():
            raise InvalidArgumentError(f"{arg}: {directory} must not exist")
    if DISABLE_VERIFY_UPSTREAMS_IGNORES_SENTINEL in (args.ignores or set()):
        args.ignore = []
    if args.ignores is None:
        args.ignores = LENIENT_FILE_ERROR_IGNORES


def _normalize_announcements_options(args: argparse.Namespace) -> None:
    if args.command not in ("announcements",):
        return
    directory: Path = args.output_dir
    directory.mkdir(parents=True, exist_ok=True)


def _normalize_send_announcements_options(args: argparse.Namespace) -> None:
    if args.command not in ("send-announcements",):
        return
    directory: Path = args.announcements_dir
    if not args.announcements_dir / "announcements.json":
        raise InvalidArgumentError(
            f"'announcements.json' does not exist in directory {directory}!"
        )
    if args.send_actions is None:
        args.send_actions = set(ALLOWED_SEND_ACTIONS)


def parse_args(program_name: str, args: list[str]) -> argparse.Namespace:
    """
    Parse and coerce the command line arguments.

    :arg program_name: The name of the program
    :arg args: A list of the command line arguments
    :returns: A :python:`argparse.Namespace`
    :raises InvalidArgumentError: Whenever there's something wrong with the arguments.
    """
    build_parser = argparse.ArgumentParser(add_help=False)
    build_parser.add_argument(
        "ansible_version",
        type=PypiVer,
        help="The X.Y.Z version of Ansible that this will be for",
    )
    build_parser.add_argument(
        "--data-dir", default=".", help="Directory to read .build and .deps files from"
    )

    build_write_data_parser = argparse.ArgumentParser(
        add_help=False, parents=[build_parser]
    )
    build_write_data_parser.add_argument(
        "--dest-data-dir",
        default=None,
        help="Directory to write .build and .deps files to,"
        " as well as changelog and porting guide if applicable."
        "  Defaults to --data-dir",
    )
    cache_parser = argparse.ArgumentParser(add_help=False)
    cache_parser.add_argument(
        "--collection-cache",
        default=argparse.SUPPRESS,
        help="Directory of cached collection tarballs.  Will be"
        " used if a collection tarball to be downloaded exists"
        " in here, and will be populated when downloading new"
        " tarballs.",
    )

    build_step_parser = argparse.ArgumentParser(add_help=False)
    build_step_parser.add_argument(
        "--build-file",
        default=None,
        help="File containing the list of collections with version"
        " ranges.  This is considered to be relative to"
        " --build-data-dir.  The default is"
        " $DEFAULT_FILE_BASE-X.Y.build",
    )
    build_step_parser.add_argument(
        "--deps-file",
        default=None,
        help="File which will be written containing the list of"
        " collections at versions which were included in this version"
        " of Ansible.  This is considered to be relative to"
        " --build-data-dir.  The default is"
        " $BASENAME_OF_BUILD_FILE-X.Y.Z.deps",
    )
    build_step_parser.add_argument(
        "--constraints-file",
        default=None,
        help="File containing a list of constraints for collections"
        " included in Ansible.  This is considered to be relative to"
        " --build-data-dir.  The default is"
        " $BASENAME_OF_BUILD_FILE-X.Y.constraints",
    )

    feature_freeze_parser = argparse.ArgumentParser(add_help=False)
    feature_freeze_parser.add_argument(
        "--feature-frozen",
        action="store_true",
        help="If this is given, then do not allow collections whose"
        " version implies there are new features.",
    )

    galaxy_file_parser = argparse.ArgumentParser(add_help=False)
    galaxy_file_parser.add_argument(
        "--galaxy-file",
        default=None,
        help="Galaxy galaxy-requirements.yaml style file which will be"
        " written containing the list of collections at versions which"
        " were included in this version of Ansible.  This is"
        " considered to be relative to --build-data-dir.  The default"
        " is $BASENAME_OF_BUILD_FILE-X.Y.Z.yaml",
    )

    # Delay import to avoid potential import loops
    from antsibull import __version__ as _ver  # pylint: disable=import-outside-toplevel

    parser = get_toplevel_parser(
        prog=program_name,
        package="antsibull",
        description="Script to manage building Ansible",
        package_version=_ver,
    )

    subparsers = parser.add_subparsers(
        title="Subcommands",
        dest="command",
        help="for help use antsibull-build SUBCOMMANDS -h",
    )
    subparsers.required = True

    new_parser = subparsers.add_parser(
        "new-ansible",
        parents=[build_write_data_parser],
        description="Generate a new build description from the"
        " latest available versions of ansible-core and the"
        " included collections",
    )
    new_parser.add_argument(
        "--pieces-file",
        default=None,
        help="File containing a list of collections to include.  This is"
        " considered to be relative to --data-dir.  The default is"
        f" {DEFAULT_PIECES_FILE}",
    )
    new_parser.add_argument(
        "--build-file",
        default=None,
        help="File which will be written which contains the list"
        " of collections with version ranges.  This is considered to be"
        " relative to --dest-data-dir.  The default is"
        " $BASENAME_OF_PIECES_FILE-X.Y.build",
    )
    new_parser.add_argument(
        "--allow-prereleases",
        action="store_true",
        default=False,
        help="Allow prereleases of collections to be included in the build" " file",
    )
    new_parser.add_argument(
        "--constraints-file",
        default=None,
        help="File containing a list of constraints for collections"
        " included in Ansible.  This is considered to be relative to"
        " --build-data-dir.  The default is"
        " $BASENAME_OF_PIECES_FILE-X.Y.constraints",
    )

    prepare_parser = subparsers.add_parser(
        "prepare",
        parents=[
            build_write_data_parser,
            build_step_parser,
            feature_freeze_parser,
            galaxy_file_parser,
        ],
        description="Collect dependencies for an Ansible release",
    )
    prepare_parser.add_argument(
        "--tags-file",
        nargs="?",
        const="DEFAULT",
        help="Whether to include a tags data file in --dest-data-dir."
        " By default, the tags data file is stored in --dest-data-dir"
        f" as {DEFAULT_FILE_BASE}-X.Y.Z-tags.yaml."
        " --tags-file takes an optional argument to change the filename.",
    )

    build_single_parser = subparsers.add_parser(
        "single",
        parents=[
            build_write_data_parser,
            cache_parser,
            build_step_parser,
            feature_freeze_parser,
            galaxy_file_parser,
        ],
        description="Build a single-file Ansible" " [deprecated]",
    )
    build_single_parser.add_argument(
        "--sdist-dir",
        default=".",
        help="Directory to write the generated sdist tarball to",
    )
    build_single_parser.add_argument(
        "--debian",
        action="store_true",
        help="Include Debian/Ubuntu packaging files in"
        " the resulting output directory",
    )
    build_single_parser.add_argument(
        "--tags-file",
        nargs="?",
        const="DEFAULT",
        help="Whether to include a tags data file in --dest-data-dir and the sdist."
        " By default, the tags data file is stored in --dest-data-dir"
        f" as {DEFAULT_FILE_BASE}-X.Y.Z-tags.yaml."
        " --tags-file takes an optional argument to change the filename."
        " The tags data file in the sdist is always named 'tags.yaml'",
    )

    package_file_parser = argparse.ArgumentParser(add_help=False)
    package_file_parser.add_argument(
        "--debian",
        action="store_true",
        help="Include Debian/Ubuntu packaging files in"
        " the resulting output directory",
    )
    package_file_parser.add_argument(
        "--tags-file",
        nargs="?",
        const="DEFAULT",
        help="Whether to include a tags data file in the sdist."
        " By default, the tags data file is stored in --data-dir"
        f" as {DEFAULT_FILE_BASE}-X.Y.Z-tags.yaml."
        " --tags-file takes an optional argument to change the filename."
        " The tags data file in the sdist is always named 'tags.yaml'",
    )

    rebuild_single_parser = subparsers.add_parser(
        "rebuild-single",
        parents=[
            build_write_data_parser,
            cache_parser,
            build_step_parser,
            package_file_parser,
        ],
        description="Rebuild a single-file Ansible from" " a dependency file",
    )
    rebuild_single_parser.add_argument(
        "--sdist-dir",
        default=".",
        help="Directory to write the generated sdist tarball to",
    )
    rebuild_single_parser.add_argument(
        "--sdist-src-dir",
        help="Copy the files from which the source distribution is"
        " created to the specified directory. This is mainly useful"
        " for debugging antsibull-build",
    )

    subparsers.add_parser(
        "changelog",
        parents=[build_write_data_parser, cache_parser],
        description="Build the Ansible changelog",
    )

    validate_deps = subparsers.add_parser(
        "validate-deps", description="Validate collection dependencies"
    )

    validate_deps.add_argument(
        "collection_root",
        help="Path to a ansible_collections directory containing a"
        " collection tree to check.",
    )
    validate_tags_shared = argparse.ArgumentParser(add_help=False)
    validate_tags_shared.add_argument(
        "-I",
        "--ignore",
        action="append",
        help="Ignore these collections when reporting errors.",
        default=[],
    )
    validate_tags_shared.add_argument(
        "--ignores-file",
        help="Path to a file with newline separated list of collections to ignore",
        type=argparse.FileType("r"),
    )
    validate_tags_shared.add_argument(
        "-E",
        "--error-on-useless-ignores",
        action=BooleanOptionalAction,
        dest="error_on_useless_ignores",
        default=True,
        help="By default, useless ignores (e.g. passing"
        " `--ignore collection.collection` when that collection is"
        " properly tagged) will be considered an error.",
    )

    validate_tags = subparsers.add_parser(
        "validate-tags",
        parents=[build_parser, validate_tags_shared],
        description="Ensure that collection versions in an Ansible release are tagged"
        " in collections' respective git repositories.",
    )
    validate_tags.add_argument(
        "--deps-file",
        default=None,
        help="File which contains the list of collections and"
        " versions which were included in this version of Ansible."
        "  This is considered to be relative to --data-dir."
        f"  The default is {DEFAULT_FILE_BASE}-X.Y.Z.deps",
    )
    validate_tags.add_argument(
        "-o",
        "--output",
        help="Path to output a collection tag data file."
        " If this is ommited, no tag data will be written",
    )

    validate_tags_file = subparsers.add_parser(
        "validate-tags-file",
        parents=[validate_tags_shared],
        description="Ensure that collection versions in an Ansible release are tagged"
        " in collections' respective git repositories."
        " This validates the tags file generated by"
        " the 'validate-tags' subcommand.",
    )
    validate_tags_file.add_argument("tags_file")

    generate_package_files = subparsers.add_parser(
        "generate-package-files",
        description=generate_package_files_command.__doc__,
        parents=[build_parser, build_step_parser, package_file_parser],
    )
    generate_package_files.add_argument(
        "-p",
        "--package-dir",
        required=True,
        help="Directory in which to write the package files",
    )
    generate_package_files.add_argument(
        "-c", "--collections-dir", help="Defaults to {PACKAGE_DIR}/ansible_collections"
    )

    verify_upstream_parser = subparsers.add_parser(
        "verify-upstreams",
        parents=[
            cache_parser,
        ],
        description=verify_upstream_command.__doc__,
    )
    verify_upstream_parser.add_argument("tags_file")
    verify_upstream_parser.add_argument(
        "-g",
        "--glob",
        dest="globs",
        action="append",
        help="Only check collections that match the glob(s)",
    )
    _choices = [v.name for v in FileError] + [DISABLE_VERIFY_UPSTREAMS_IGNORES_SENTINEL]
    verify_upstream_parser.add_argument(
        "-I",
        "--ignore",
        action="append",
        dest="ignores",
        type=FileError,
        help=f"List of upstream verification errors to ignore. Choices: {_choices}."
        f" Default: {[v.name for v in LENIENT_FILE_ERROR_IGNORES]}.",
    )
    verify_upstream_parser.add_argument(
        "-O",
        "--error-output",
        type=Path,
        help="Path to a file to output errors",
        required=True,
    )
    verify_upstream_parser.add_argument(
        "--tree-dir",
        type=Path,
        help="Directory in which to create a collection tree",
    )
    verify_upstream_parser.add_argument(
        "--checkouts-dir",
        type=Path,
        help="Directory in which to clone collection repositories",
    )
    # Private argument to use a special download directory
    verify_upstream_parser.add_argument(
        "--download-dir", help=argparse.SUPPRESS, type=Path
    )

    sanity_test_parser = subparsers.add_parser(
        "sanity-tests",
        help=sanity_tests_command.__doc__,
    )
    sanity_test_parser.add_argument("collection_paths", type=Path, nargs="+")
    sanity_test_parser.add_argument(
        "-O",
        "--error-output",
        type=Path,
        help="Path to a YAML file to output errors",
        required=True,
    )
    sanity_test_parser.add_argument(
        "-t",
        "--test",
        action="append",
        help=f"Sanity tests to run. Default: {SANITY_TESTS_DEFAULT}",
        dest="tests",
    )
    sanity_test_parser.add_argument(
        "--clean",
        action=BooleanOptionalAction,
        default=True,
        help="Whether to clean collections' test output directories."
        " Default: %(default)s",
    )
    sanity_test_parser.add_argument(
        "--quiet",
        action=BooleanOptionalAction,
        default=False,
        help="Whether to show sanity test output as it runs. Default: %(default)s",
    )
    sanity_test_parser.add_argument("--ansible-test-bin", default="ansible-test")

    announcements_parser = subparsers.add_parser(
        "announcements",
        parents=[build_parser, build_step_parser],
        description=announcements_command.__doc__,
    )
    announcements_parser.add_argument(
        "-O", "--output-dir", type=Path, default=DEFAULT_ANNOUNCEMENTS_DIR
    )
    announcements_parser.add_argument(
        "--dist-dir",
        help="Directory containing dists to match against those uploaded to PyPI",
        type=Path,
    )
    announcements_parser.add_argument(
        "--send",
        action="store_true",
        help="Interactively send announcements using send-announcements command"
        " (with default options) after generating them",
    )

    send_announcements_parser = subparsers.add_parser(
        "send-announcements", description=send_announcements_command.__doc__
    )
    send_announcements_parser.add_argument(
        "--announcements-dir", type=Path, default=DEFAULT_ANNOUNCEMENTS_DIR
    )
    send_announcements_parser.add_argument(
        "--clipboard",
        default=True,
        action=BooleanOptionalAction,
        help="Whether to allow the command to write to the system clipboard."
        " Default: %(default)s",
    )
    send_announcements_parser.add_argument(
        "-A",
        "--action",
        action="append",
        choices=list(ALLOWED_SEND_ACTIONS),
        help="Which actions to perform."
        " --action can be specified multiple times."
        " Defaults to performing all actions.",
        dest="send_actions",
    )

    parsed_args: argparse.Namespace = parser.parse_args(args)

    # Validation and coercion
    normalize_toplevel_options(parsed_args)
    _normalize_commands(parsed_args)
    _normalize_build_options(parsed_args)
    _normalize_build_write_data_options(parsed_args)
    _normalize_new_release_options(parsed_args)
    _normalize_release_build_options(parsed_args)
    _normalize_validate_tags_options(parsed_args)
    _normalize_release_rebuild_options(parsed_args)
    _normalize_validate_tags_file_options(parsed_args)
    _normalize_generate_package_files_options(parsed_args)
    _normalize_verify_upstream_options(parsed_args)
    _normalize_announcements_options(parsed_args)
    _normalize_send_announcements_options(parsed_args)

    return parsed_args


def run(args: list[str]) -> int:
    """
    Run the program.

    :arg args: A list of command line arguments.  Typically :python:`sys.argv`.
    :returns: A program return code.  0 for success, integers for any errors.  These are documented
        in :func:`main`.
    """
    flog = mlog.fields(func="run")
    flog.fields(raw_args=args).info("Enter")

    program_name = os.path.basename(args[0])
    try:
        parsed_args: argparse.Namespace = parse_args(program_name, args[1:])
    except InvalidArgumentError as e:
        print(e)
        return 2

    try:
        cfg = load_config(parsed_args.config_file)
        flog.fields(config=cfg).info("Config loaded")
    except ConfigError as e:
        print(e)
        return 2

    context_data = app_context.create_contexts(args=parsed_args, cfg=cfg)
    with app_context.app_and_lib_context(context_data) as (app_ctx, dummy_):
        # TODO: Call `model_dump()` instead of deprecated `dict()`
        # once support for pydantic v1/antsibull-core v2 is dropped
        twiggy.dict_config(app_ctx.logging_cfg.dict())
        flog.debug("Set logging config")

        flog.fields(command=parsed_args.command).info("Action")
        return ARGS_MAP[parsed_args.command]()


def main() -> int:
    """
    Entrypoint called from the script.

    console_scripts call functions which take no parameters.  However, it's hard to test a function
    which takes no parameters so this function lightly wraps :func:`run`, which actually does the
    heavy lifting.

    :returns: A program return code.

    Return codes:
        :0: Success
        :1: Unhandled error.  See the Traceback for more information.
        :2: There was a problem with the command line arguments
        :3: version in an input file does not match with the version specified on the command line
        :4: Needs to be run on a newer version of Python
    """
    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
