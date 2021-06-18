# antsibull -- Ansible Build Scripts
[![Python linting badge](https://github.com/ansible-community/antsibull/workflows/Python%20linting/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22Python+linting%22+branch%3Amain)
[![Python testing badge](https://github.com/ansible-community/antsibull/workflows/Python%20testing/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22Python+testing%22+branch%3Amain)
[![Build CSS testing badge](https://github.com/ansible-community/antsibull/workflows/Build%20CSS/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22Build+CSS%22+branch%3Amain)
[![dumb PyPI on GH pages badge](https://github.com/ansible-community/antsibull/workflows/👷%20dumb%20PyPI%20on%20GH%20pages/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22👷+dumb+PyPI+on+GH+pages%22+branch%3Amain)
[![Codecov badge](https://img.shields.io/codecov/c/github/ansible-community/antsibull)](https://codecov.io/gh/ansible-community/antsibull)

Tooling for building various things related to Ansible

Scripts that are here:

* antsibull-build - Builds Ansible-2.10+ from component collections ([docs](docs/build-ansible.rst))
* antsibull-docs - Extracts documentation from ansible plugins
* antsibull-lint - Right now only validates ``changelogs/changelog.yaml`` files ([docs](docs/changelog.yaml-format.md))

This also includes a [Sphinx extension](https://www.sphinx-doc.org/en/master/) `sphinx_antsibull_ext` which provides a minimal CSS file to render the output of `antsibull-docs` correctly.

A related project is [antsibull-changelog](https://pypi.org/project/antsibull-changelog/), which is in its [own repository](https://github.com/ansible-community/antsibull-changelog/).

Scripts are created by poetry at build time.  So if you want to run from
a checkout, you'll have to run them under poetry::

    python3 -m pip install poetry
    poetry install  # Installs dependencies into a virtualenv
    poetry run antsibull-build --help

.. note:: When installing a package published by poetry, it is best to use
    pip >= 19.0.  Installing with pip-18.1 and below could create scripts which
    use pkg_resources which can slow down startup time (in some environments by
    quite a large amount).

Unless otherwise noted in the code, it is licensed under the terms of the GNU
General Public License v3 or, at your option, later.

antsibull is covered by the [Ansible Code of Conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html).

## Using the Sphinx extension

Include it in your Sphinx configuration ``conf.py``::

```
# Add it to 'extensions':
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'notfound.extension', 'sphinx_antsibull_ext']
```

## Updating the CSS file for the Sphinx extension

The CSS file [sphinx_antsibull_ext/antsibull-minimal.css](https://github.com/ansible-community/antsibull/blob/main/sphinx_antsibull_ext/antsibull-minimal.css) is built from [sphinx_antsibull_ext/css/antsibull-minimal.scss](https://github.com/ansible-community/antsibull/blob/main/sphinx_antsibull_ext/src/antsibull-minimal.scss) using [SASS](https://sass-lang.com/) and [postcss](https://postcss.org/) using [autoprefixer](https://github.com/postcss/autoprefixer) and [cssnano](https://cssnano.co/).

Use the script `build.sh` in `sphinx_antsibull_ext/css/` to build the `.css` file from the `.scss` file:

```
cd sphinx_antsibull_ext/css/
./build-css.sh
```

For this to work, you need to make sure that `sassc` and `postcss` are on your path and that the autoprefixer and nanocss modules are installed:

```
# Debian:
apt-get install sassc

# PostCSS, autoprefixer and cssnano require nodejs/npm:
npm install -g autoprefixer cssnano postcss postcss-cli
```

## Creating a new release:

If you want to create a new release::

    poetry build
    poetry publish  # Uploads to pypi.  Be sure you really want to do this

    git tag $VERSION_NUMBER
    git push --tags
    vim pyproject.toml    # Bump the version number
    git commit -m 'Update the version number for the next release' pyproject.toml
    git push
