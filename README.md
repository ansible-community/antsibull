# antsibull -- Ansible Build Scripts
[![Python linting badge](https://github.com/ansible-community/antsibull/workflows/Python%20linting/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22Python+linting%22+branch%3Amain)
[![Python testing badge](https://github.com/ansible-community/antsibull/workflows/Python%20testing/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22Python+testing%22+branch%3Amain)
[![dumb PyPI on GH pages badge](https://github.com/ansible-community/antsibull/workflows/👷%20dumb%20PyPI%20on%20GH%20pages/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22👷+dumb+PyPI+on+GH+pages%22+branch%3Amain)
[![Codecov badge](https://img.shields.io/codecov/c/github/ansible-community/antsibull)](https://codecov.io/gh/ansible-community/antsibull)

Tooling for building various things related to Ansible

Scripts that are here:

* antsibull-build - Builds Ansible-2.10+ from component collections ([docs](docs/build-ansible.rst))
* antsibull-lint - Soon to be deprecated; collection docs linting functionality is now part of antsibull-docs, and ``changelogs/changelog.yaml`` validation functionality is now part of antsibull-changelog.

This also includes a [Sphinx extension](https://www.sphinx-doc.org/en/master/) `sphinx_antsibull_ext` which provides a minimal CSS file to render the output of `antsibull-docs` correctly.

Related projects are [antsibull-changelog](https://pypi.org/project/antsibull-changelog/) and [antsibull-docs](https://pypi.org/project/antsibull-docs/), which are in their own repositories ([antsibull-changelog repository](https://github.com/ansible-community/antsibull-changelog/), [antsibull-docs repository](https://github.com/ansible-community/antsibull-docs/)).

You can find a list of changes in [the Antsibull changelog](./CHANGELOG.rst).

Unless otherwise noted in the code, it is licensed under the terms of the GNU
General Public License v3 or, at your option, later.

antsibull is covered by the [Ansible Code of Conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html).

## Running from source

Please note that to run antsibull from source, you need to install some related projects adjacent to the antsibull checkout.  More precisely, assuming you checked out the antsibull repository in a directory `./antsibull/`, you need to check out the following projects in the following locations:

- [antsibull-changelog](https://github.com/ansible-community/antsibull-changelog/) needs to be checked out in `./antsibull-changelog/`.
- [antsibull-core](https://github.com/ansible-community/antsibull-core/) needs to be checked out in `./antsibull-core/`.
- [antsibull-docs](https://github.com/ansible-community/antsibull-docs/) needs to be checked out in `./antsibull-docs/`.

This can be done as follows:

    git clone https://github.com/ansible-community/antsibull-changelog.git
    git clone https://github.com/ansible-community/antsibull-core.git
    git clone https://github.com/ansible-community/antsibull-docs.git
    git clone https://github.com/ansible-community/antsibull.git
    cd antsibull

Scripts are created by poetry at build time.  So if you want to run from a checkout, you'll have to run them under poetry::

    python3 -m pip install poetry
    poetry install  # Installs dependencies into a virtualenv
    poetry run antsibull-build --help

Note: When installing a package published by poetry, it is best to use pip >= 19.0.  Installing with pip-18.1 and below could create scripts which use pkg_resources which can slow down startup time (in some environments by quite a large amount).

## Creating a new release:

If you want to create a new release::

    vim changelogs/fragment/$VERSION_NUMBER.yml  # create 'release_summary:' fragment
    antsibull-changelog release --version $VERSION_NUMBER
    git add CHANGELOG.rst changelogs
    git commit -m "Release $VERSION_NUMBER."
    poetry build
    poetry publish  # Uploads to pypi.  Be sure you really want to do this

    git tag $VERSION_NUMBER
    git push --tags
    vim pyproject.toml    # Bump the version number
    git commit -m 'Update the version number for the next release' pyproject.toml
    git push
