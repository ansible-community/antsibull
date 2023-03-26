# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import os
from pathlib import Path

import nox

DEFAULT_MODE = os.environ.get("OTHER_ANTSIBULL_MODE", "auto")
IN_CI = "GITHUB_ACTIONS" in os.environ
ALLOW_EDITABLE = os.environ.get("ALLOW_EDITABLE", str(not IN_CI)).lower() in (
    "1",
    "true",
)

# Always install latest pip version
os.environ["VIRTUALENV_DOWNLOAD"] = "1"
nox.options.sessions = "lint", "test"


def install(session: nox.Session, *args, editable=False, **kwargs):
    # nox --no-venv
    if isinstance(session.virtualenv, nox.virtualenv.PassthroughEnv):
        session.warn(f"No venv. Skipping installation of {args}")
        return
    # Don't install in editable mode in CI or if it's explicitly disabled.
    # This ensures that the wheel contains all of the correct files.
    if editable and ALLOW_EDITABLE:
        args = ("-e", *args)
    session.install(*(str(arg) for arg in args), "-U", **kwargs)


def other_antsibull(
    mode: str | None = None,
) -> list[str | Path]:
    if mode is None:
        mode = DEFAULT_MODE
    to_install: list[str | Path] = []
    args = ("antsibull-core", "antsibull-changelog")
    for project in args:
        path = Path("../", project)
        path_exists = path.is_dir()
        if mode == "auto":
            if path_exists:
                mode = "local"
            else:
                mode = "git"
        if mode == "local":
            if not path_exists:
                raise ValueError(f"Cannot install {project}! {path} does not exist!")
            if ALLOW_EDITABLE:
                to_install.append("-e")
            to_install.append(path)
        elif mode == "git":
            to_install.append(
                f"{project} @ "
                f"https://github.com/ansible-community/{project}/archive/main.tar.gz"
            )
        elif mode == "pypi":
            to_install.append(project)
        else:
            raise ValueError(f"install_other_antsibull: invalid argument mode={mode!r}")
    return to_install


@nox.session(python=["3.9", "3.10", "3.11"])
def test(session: nox.Session):
    install(
        session,
        ".[test]",
        *other_antsibull(),
        editable=True,
    )
    session.run(
        "pytest",
        "--cov-branch",
        "--cov=antsibull",
        *session.posargs,
    )


@nox.session
def coverage_release(session: nox.Session):
    """
    Build a test release and report coverage
    """
    install(
        session,
        ".",
        *other_antsibull(),
        "ansible-core",
        "coverage",
        editable=True,
    )

    build_command = (
        "coverage run -p --source antsibull -m antsibull.cli.antsibull_build"
    )
    posargs = session.posargs
    # Set default settings
    if not posargs:
        posargs = (
            "-e",
            "antsibull_ansible_version=7.99.0",
            "-e",
            "antsibull_ansible_git_version=stable-2.14",
        )
    collections = Path(session.create_tmp()).joinpath("collections")
    os.environ["ANSIBLE_COLLECTIONS_PATH"] = str(collections)
    session.run(
        "ansible-galaxy",
        "collection",
        "install",
        "git+https://github.com/ansible-collections/community.general",
    )
    session.run(
        "ansible-playbook",
        "-vv",
        "playbooks/build-single-release.yaml",
        *posargs,
        "-e",
        f"antsibull_build_command={build_command!r}",
    )
    session.run("coverage", "combine", *Path(".").glob(".coverage.*"))
    session.run("coverage", "report")
    session.run("coverage", "xml", "-i")


@nox.session
def lint(session: nox.Session):
    session.notify("codeqa")
    session.notify("typing")


@nox.session
def codeqa(session: nox.Session):
    install(session, ".[codeqa]", *other_antsibull(), editable=True)
    session.run("flake8", "src/antsibull", *session.posargs)
    session.run("pylint", "--rcfile", ".pylintrc.automated", "src/antsibull")
    session.run("reuse", "lint")


@nox.session
def typing(session: nox.Session):
    install(session, ".[typing]", *other_antsibull(), editable=True)
    session.run("mypy", "src/antsibull")

    purelib = session.run(
        "python",
        "-c",
        "import sysconfig; print(sysconfig.get_path('purelib'))",
        silent=True,
    ).strip()
    platlib = session.run(
        "python",
        "-c",
        "import sysconfig; print(sysconfig.get_path('platlib'))",
        silent=True,
    ).strip()
    session.run(
        "pyre",
        "--source-directory",
        "src",
        "--search-path",
        purelib,
        "--search-path",
        platlib,
        "--search-path",
        "stubs/",
    )


def _repl_version(session: nox.Session, new_version: str):
    with open("pyproject.toml", "r+") as fp:
        lines = tuple(fp)
        fp.seek(0)
        for line in lines:
            if line.startswith("version = "):
                line = f'version = "{new_version}"\n'
            fp.write(line)


def check_no_modifications(session: nox.Session) -> None:
    modified = session.run(
        "git",
        "status",
        "--porcelain=v1",
        "--untracked=normal",
        external=True,
        silent=True,
    )
    if modified:
        session.error(
            "There are modified or untracked files. "
            "Commit, restore, or remove them before running this"
        )


@nox.session
def bump(session: nox.Session):
    check_no_modifications(session)
    if len(session.posargs) not in (1, 2):
        session.error(
            "Must specify 1-2 positional arguments: nox -e bump -- <version> "
            "[ <release_summary_message> ]."
            " If release_summary_message has not been specified, "
            "a file changelogs/fragments/<version>.yml must exist"
        )
    version = session.posargs[0]
    fragment_file = Path(f"changelogs/fragments/{version}.yml")
    if len(session.posargs) == 1:
        if not fragment_file.is_file():
            session.error(
                f"Either {fragment_file} must already exist, "
                "or two positional arguments must be provided."
            )
    install(session, "antsibull-changelog", "tomli ; python_version < '3.11'")
    _repl_version(session, version)
    if len(session.posargs) > 1:
        fragment = session.run(
            "python",
            "-c",
            "import yaml ; "
            f"print(yaml.dump(dict(release_summary={repr(session.posargs[1])})))",
            silent=True,
        )
        with open(fragment_file, "w") as fp:
            print(fragment, file=fp)
        session.run("git", "add", "pyproject.toml", fragment_file, external=True)
        session.run("git", "commit", "-m", f"Prepare {version}.", external=True)
    session.run("antsibull-changelog", "release")
    session.run(
        "git",
        "add",
        "CHANGELOG.rst",
        "changelogs/changelog.yaml",
        "changelogs/fragments/",
        external=True,
    )
    install(session, ".")  # Smoke test
    session.run("git", "commit", "-m", f"Release {version}.", external=True)
    session.run(
        "git",
        "tag",
        "-a",
        "-m",
        f"antsibull {version}",
        "--edit",
        version,
        external=True,
    )


@nox.session
def publish(session: nox.Session):
    check_no_modifications(session)
    install(session, "hatch")
    session.run("hatch", "publish", *session.posargs)
    session.run("git", "push", "--follow-tags")
    version = session.run("hatch", "version", silent=True).strip()
    _repl_version(session, f"{version}.post0")
    session.run("git", "commit", "pyproject.toml")
    session.run("git", "commit", "-m", "Post-release version bump.", external=True)


@nox.session
def install_env(session: nox.Session):
    """
    Install antsibull and the other project in the the local environment.
    Invoke with `nox -e install_env --no-venv`
    """
    session.run(
        "pip",
        "install",
        "-U",
        ".",
        *other_antsibull(),
        *session.posargs,
        external=True,
        editable=True,
    )
