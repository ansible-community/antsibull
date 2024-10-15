<!--
```markdown
<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

#  **Antsibull** — *Ansible Build Scripts* 🚀

### A powerful tool for building various Ansible-related things! 🎯  
&nbsp;

<p align="center">
    <a href="https://matrix.to/#/#antsibull:ansible.com">
        <img src="https://img.shields.io/matrix/antsibull:ansible.com.svg?server_fqdn=ansible-accounts.ems.host&label=Join%20the%20Conversation&logo=matrix" alt="💬 Discuss on Matrix">
    </a>
    <a href="https://github.com/ansible-community/antsibull/actions/workflows/nox.yml">
        <img src="https://github.com/ansible-community/antsibull/actions/workflows/nox.yml/badge.svg" alt="🚀 Nox">
    </a>
    <a href="https://github.com/ansible-community/antsibull/actions?query=workflow%3A%22👷+dumb+PyPI+on+GH+pages%22+branch%3Amain">
        <img src="https://github.com/ansible-community/antsibull/workflows/👷%20dumb%20PyPI%20on%20GH%20pages/badge.svg?event=push&branch=main" alt="👷‍♂️ PyPI on GH">
    </a>
    <a href="https://codecov.io/gh/ansible-community/antsibull">
        <img src="https://img.shields.io/codecov/c/github/ansible-community/antsibull" alt="Codecov badge">
    </a>
</p>

---

## 🚧 **Scripts Available** 

✨ **`antsibull-build`** — Builds Ansible 6+ from component collections.  
📜 [Documentation](https://github.com/ansible-community/antsibull/blob/main/docs/build-ansible.rst)  
🔗 Related projects:  
    - [antsibull-changelog](https://pypi.org/project/antsibull-changelog/)  
    - [antsibull-docs](https://pypi.org/project/antsibull-docs/)

📄 **Changelog**  
You can find all the changes in the [Antsibull changelog](https://github.com/ansible-community/antsibull/blob/main/CHANGELOG.md).  


🚨 Covered by the [Ansible Code of Conduct](https://docs.ansible.com/ansible/latest/community/code_of_conduct.html).  

---

## 🛡️ **Licensing**

This repository follows the [REUSE specification](https://reuse.software).  
💼 The default license: **GNU Public License v3+** ([Details here](LICENSES/GPL-3.0-or-later.txt)).  
💡 Code derived from CPython is licensed under Python 2.0 ([Details here](LICENSES/Python-2.0.1.txt)).

---

## 🔢 **Versioning & Compatibility**

Since version **0.1.0**, antsibull follows **semantic versioning** 🧮 and ensures no breaking changes to the command line API during a major release cycle.

❗ **Note:** antsibull is not meant to be used as a library.  

---

## 💻 **Development** 

### Quick Start

🚀 To run tests, install and run `nox`. That’s it! 🎉  
It will create virtual environments in `.nox` and handle everything for you! 💡

---

## 🛠️ **Antsibull Development Projects**

Antsibull depends on several projects:  
`antsibull-core`, `antsibull-changelog`, `antsibull-docs-parser`, `antsibull-docutils`, `antsibull-fileutils`.  

Use the `OTHER_ANTSIBULL_MODE` environment variable to customize how these dependencies are installed:

1. **auto** — Default behavior.  
2. **local** — Install from local paths.  
3. **git** — Install from the GitHub main branch.  
4. **pypi** — Install the latest version from PyPI.


## 🧪 **Running Specific Tests**

You can run various tests using `nox` by executing the commands below. Each command corresponds to a specific testing type:

| Command                                     | Description                                                         |
|---------------------------------------------|---------------------------------------------------------------------|
| `nox -e test`                               | 🔍 **Run Unit Tests**: Execute all unit tests.                     |
| `nox -e lint`                               | 🧹 **Run Linters**: Execute all linters to check code style.       |
| `nox -e formatters`                         | ✨ **Run Formatters**: Execute `isort` and `black` for formatting.  |
| `nox -e codeqa`                             | 📊 **Run Code Quality Checks**: Execute `flake8`, `pylint`, `reuse lint`, and `antsibull-changelog lint`. |
| `nox -e typing`                             | 🧾 **Run Type Checking**: Execute `mypy` for type validation.      |
| `nox -e coverage_release`                   | 🏗️ **Build Test Ansible Release**: This is expensive, so it's not run by default. |
| `nox -e check_package_files`                | 📦 **Generate Package Files Tests**: This is somewhat expensive and thus not run by default. |
| `nox -e coverage`                           | 📈 **Display Combined Coverage**: Shows coverage results after running the specified tests. |

### 📝 Additional Commands

- **List All Test Sessions**: Run `nox -l` to see all available test sessions.

### 📌 **Note**
Some tests, like `coverage_release` and `check_package_files`, are resource-intensive and are not run by default. Make sure to consider your environment's capacity before executing these commands!

---

## ⚙️ **Complete Local Development Setup**  

Follow these steps to clone and install antsibull along with its dependencies:

```bash
git clone https://github.com/ansible-community/antsibull-changelog.git
git clone https://github.com/ansible-community/antsibull-core.git
git clone https://github.com/ansible-community/antsibull-docs-parser.git
git clone https://github.com/ansible-community/antsibull-docutils.git
git clone https://github.com/ansible-community/antsibull.git
cd antsibull
python3 -m venv venv
source ./venv/bin/activate
pip install -e '.[dev]' -e ../antsibull-changelog -e ../antsibull-core -e ../antsibull-docs-parser -e ../antsibull-docutils
nox
```

## 🚀 Creating a New Release

Follow these steps to create a new release smoothly:

### 1. 🔧 Bump the Version  
Run the following command to start the release process:

```bash
nox -e bump -- <version> <release_summary_message>
```

This will:

    • 📈 Update the package version in src/antsibull/__init__.py.
    • 📄 Generate a new changelog fragment in changelogs/fragments/<version>.yml with a summary section.
    • 📝 Run antsibull-changelog release and stage the files for git.
    • 📦 Commit the changes with the message Release <version>. and create a tag:

    ```bash
    git tag -a -m 'antsibull <version>' <version>
    ```

    • 🛠️ Build an sdist and wheel using hatch build --clean, and clean up old artifacts in the dist/ folder.

### 2. 🔄 Push Changes

Push the changes and tags to your repository:

```bash
git push
```

### 3. 🏗️ Publish the Release

Once the CI tests pass on GitHub, publish the release to PyPI with:

```bash
nox -e publish
```

This will:
- 🚀 Publish the package to PyPI using hatch publish.
- 🔄 Bump the version to <version>.post0 for post-release.
- 📋 Commit the version bump with:

    ```bash
    git commit -m 'Post-release version bump.'
    ```

### 4. 🔧 Push Final Changes

Finally, push the new tags and changes:

```bash
git push --follow-tags
```
