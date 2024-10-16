<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# antsibull-build -- Ansible Build Scripts
[![Discuss on Matrix at #antsibull:ansible.com](https://img.shields.io/matrix/antsibull:ansible.com.svg?server_fqdn=ansible-accounts.ems.host&label=Discuss%20on%20Matrix%20at%20%23antsibull:ansible.com&logo=matrix)](https://matrix.to/#/#antsibull:ansible.com)
[![Nox badge](https://github.com/ansible-community/antsibull-build/actions/workflows/nox.yml/badge.svg)](https://github.com/ansible-community/antsibull-build/actions/workflows/nox.yml)
[![dumb PyPI on GH pages badge](https://github.com/ansible-community/antsibull-build/workflows/👷%20dumb%20PyPI%20on%20GH%20pages/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull-build/actions?query=workflow%3A%22👷+dumb+PyPI+on+GH+pages%22+branch%3Amain)
[![Codecov badge](https://img.shields.io/codecov/c/github/ansible-community/antsibull-build)](https://codecov.io/gh/ansible-community/antsibull-build)
[![REUSE status](https://api.reuse.software/badge/github.com/ansible-community/antsibull-build)](https://api.reuse.software/info/github.com/ansible-community/antsibull-build)

Tooling for building various things related to Ansible

Scripts that are here:

* antsibull-build - Builds Ansible 6+ from component collections ([docs](https://github.com/ansible-community/antsibull/blob/main/docs/build-ansible.rst))

Related projects are [antsibull-changelog](https://pypi.org/project/antsibull-changelog/) and [antsibull-docs](https://pypi.org/project/antsibull-docs/), which are in their own repositories ([antsibull-changelog repository](https://github.com/ansible-community/antsibull-changelog/), [antsibull-docs repository](https://github.com/ansible-community/antsibull-docs/)). Currently antsibull-changelog is a dependency of antsibull-build. Therefore, the scripts contained in it will be available as well when installing antsibull-build.

You can find a list of changes in [the Antsibull Build changelog](https://github.com/ansible-community/antsibull-build/blob/main/CHANGELOG.md).

antsibull-build is covered by the [Ansible Code of Conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html).

## Licensing

This repository abides by the [REUSE specification](https://reuse.software).
See the copyright headers in each file for the exact license and copyright.
Summarily:

- The default license is the GNU Public License v3+
  ([`GPL-3.0-or-later`](LICENSES/GPL-3.0-or-later.txt)).
- `src/antsibull/_vendor/shutil.py` includes code derived from CPython, licensed
  under the Python 2.0 License ([`Python-2.0.1`](LICENSES/Python-2.0.1.txt)).

## Versioning and compatibility

From version 0.1.0 on, antsibull-build sticks to semantic versioning and aims at providing no backwards compatibility breaking changes **to the command line API (antsibull-build)** during a major release cycle. We might make exceptions from this in case of security fixes for vulnerabilities that are severe enough.

We explicitly exclude code compatibility. **antsibull-build is not supposed to be used as a library.** The only exception are potential dependencies with other antsibull projects (currently, none). If you want to use a certain part of antsibull-build as a library, please create an issue so we can discuss whether we add a stable interface for **parts** of the Python code. We do not promise that this will actually happen though.

## Development

Install and run `nox` to run all tests. That's it for simple contributions!
`nox` will create virtual environments in `.nox` inside the checked out project
and install the requirements needed to run the tests there.

---

antsibull-build depends on the sister antsibull-core, antsibull-changelog,
antsibull-docs-parser, antsibull-docutils, and antsibull-fileutils projects.
By default, `nox` will install development versions of these projects from
Github.
If you're hacking on antsibull-core, antsibull-changelog, antsibull-docs-parser,
antsibull-docutils and/or antsibull-fileutils alongside antsibull-build,
nox will automatically install the projects from `../antsibull-core`,
`../antsibull-changelog`, `../antsibull-docs-parser`, `../antsibull-docutils`,
and `../antsibull-fileutils` when running tests if those paths exist.
You can change this behavior through the `OTHER_ANTSIBULL_MODE` env var:

- `OTHER_ANTSIBULL_MODE=auto` — the default behavior described above
- `OTHER_ANTSIBULL_MODE=local` — install the projects from `../antsibull-core`,
  `../antsibull-changelog`, `../antsibull-docs-parser`, `../antsibull-docutils`,
  and `../antsibull-fileutils`.
  Fail if those paths don't exist.
- `OTHER_ANTSIBULL_MODE=git` — install the projects from the Github main branch
- `OTHER_ANTSIBULL_MODE=pypi` — install the latest version from PyPI

---

To run specific tests:

1. `nox -e test` to only run unit tests;
2. `nox -e lint` to run all linters;
3. `nox -e formatters` to run `isort` and `black`;
4. `nox -e codeqa` to run `flake8`, `pylint`, `reuse lint`, and `antsibull-changelog lint`;
5. `nox -e typing` to run `mypy`.
6. `nox -e coverage_release` to build a test ansible release.
   This is expensive, so it's not run by default.
7. `nox -e check_package_files` to run the generate-package-files integration tests.
   This is somewhat expensive and thus not run by default.
8. `nox -e coverage` to display combined coverage results after running `nox -e
   test coverage_release check_package_files`;

Run `nox -l` to list all test sessions.

To create a more complete local development env:

``` console
git clone https://github.com/ansible-community/antsibull-changelog.git
git clone https://github.com/ansible-community/antsibull-core.git
git clone https://github.com/ansible-community/antsibull-docs-parser.git
git clone https://github.com/ansible-community/antsibull-docutils.git
git clone https://github.com/ansible-community/antsibull-build.git
cd antsibull-build
python3 -m venv venv
. ./venv/bin/activate
pip install -e '.[dev]' -e ../antsibull-changelog -e ../antsibull-core -e ../antsibull-docs-parser -e ../antsibull-docutils
[...]
nox
```

## Creating a new release:

1. Run `nox -e bump -- <version> <release_summary_message>`. This:
   * Bumps the package version in `src/antsibull/__init__.py`.
   * Creates `changelogs/fragments/<version>.yml` with a `release_summary` section.
   * Runs `antsibull-changelog release` and adds the changed files to git.
   * Commits with message `Release <version>.` and runs `git tag -a -m 'antsibull-build <version>' <version>`.
   * Runs `hatch build --clean` to build an sdist and wheel in `dist/` and
     clean up any old artifacts in that directory.
2. Run `git push` to the appropriate remotes.
3. Once CI passes on GitHub, run `nox -e publish`. This:
   * Runs `hatch publish` to publish the sdist and wheel generated during step 1 to PyPI;
   * Bumps the version to `<version>.post0`;
   * Adds the changed file to git and runs `git commit -m 'Post-release version bump.'`;
4. Run `git push --follow-tags` to the appropriate remotes and create a GitHub release.
