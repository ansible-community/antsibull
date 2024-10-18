#!/bin/sh
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020

set -e

VERSION="8.1.0"
MAJOR="8"

# For idempotency, remove build data or built output first
rm -rf ansible-build-data built

pip3 install --user --upgrade "antsibull-build==(ANTSIBULL_VERSION)"
git clone https://github.com/ansible-community/ansible-build-data.git
mkdir -p built collection-cache
BUILD_DATA_DIR="ansible-build-data/${MAJOR}"
BUILDFILE="ansible-${MAJOR}.build"
DEPSFILE="ansible-${VERSION}.deps"

antsibull-build rebuild-single "${VERSION}" --collection-cache collection-cache --data-dir "${BUILD_DATA_DIR}" --build-file "${BUILDFILE}" --deps-file "${DEPSFILE}" --sdist-dir built --debian

echo "The result can be found in built/ansible-${VERSION}.tar.gz"

# pip3 install --user twine
# twine upload "built/ansible-${VERSION}.tar.gz"