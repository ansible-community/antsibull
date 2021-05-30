# antsibull Sphinx extension -- Provide requirements for antsibull generated documentation, and more
[![Python linting badge](https://github.com/ansible-community/antsibull/workflows/Python%20linting/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22Python+linting%22+branch%3Amain)
[![Python testing badge](https://github.com/ansible-community/antsibull/workflows/Python%20testing/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22Python+testing%22+branch%3Amain)
[![Build CSS testing badge](https://github.com/ansible-community/antsibull/workflows/Build%20CSS/badge.svg?event=push&branch=main)](https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22Build+CSS%22+branch%3Amain)
[![Codecov badge](https://img.shields.io/codecov/c/github/ansible-community/antsibull)](https://codecov.io/gh/ansible-community/antsibull)

This is the [Sphinx extension](https://www.sphinx-doc.org/en/master/) `sphinx-antsibull-ext` which provides a lexer for Ansible output and a minimal CSS file to render the output of `antsibull-docs` correctly.

Unless otherwise noted in the code, it is licensed under the terms of the GNU
General Public License v3 or, at your option, later.

## Using the Sphinx extension

Include it in your Sphinx configuration ``conf.py``::

```
# Add it to 'extensions':
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'notfound.extension', 'sphinx_antsibull_ext']
```

## Updating the CSS file

The CSS file [sphinx-extension/sphinx_antsibull_ext/antsibull-minimal.css](https://github.com/ansible-community/antsibull/blob/main/sphinx-extension/sphinx_antsibull_ext/antsibull-minimal.css) is built from [sphinx-extension/sphinx_antsibull_ext/css/antsibull-minimal.scss](https://github.com/ansible-community/antsibull/blob/main/sphinx-extension/sphinx_antsibull_ext/src/antsibull-minimal.scss) using [SASS](https://sass-lang.com/) and [postcss](https://postcss.org/) using [autoprefixer](https://github.com/postcss/autoprefixer) and [cssnano](https://cssnano.co/).

Use the script `build.sh` in `sphinx-extension/sphinx_antsibull_ext/css/` to build the `.css` file from the `.scss` file:

```
cd sphinx-extension/sphinx_antsibull_ext/css/
./build-css.sh
```

For this to work, you need to make sure that `sassc` and `postcss` are on your path and that the autoprefixer and nanocss modules are installed:

```
# Debian:
apt-get install sassc

# PostCSS, autoprefixer and cssnano require nodejs/npm:
npm install -g autoprefixer cssnano postcss postcss-cli
```
