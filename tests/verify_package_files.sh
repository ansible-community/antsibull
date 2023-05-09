#!/usr/bin/bash -x
# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

set -euo pipefail

ANTSIBULL_BUILD="${ANTSIBULL_BUILD-antsibull-build}"

generate_tag_files() {
    time bsdtar -C "${temp}" -xf "${tarball}" --strip-components=1 "${topdir}/ansible_collections"
    ${ANTSIBULL_BUILD} generate-package-files -p "${temp}" --tags-file "$@"
}

tarball="${1}"
topdir="$(basename "${tarball}" .tar.gz)"
expected_package_dir="${2}"
temp="$(mktemp -d)"
temp2="$(mktemp -d)"
trap 'rm -rf "${temp}" "${temp2}"' EXIT

generate_tag_files "${@:3}"

time python -m build --outdir "${temp2}" "${temp}" --config-setting=--quiet

mkdir -p "${temp}/dist-files"
for file in "${temp2}"/*; do
    bsdtar tf "${file}" | LC_ALL=C sort > "${temp}/dist-files/$(basename "${file}")"
done

rm -rf "${temp}/ansible_collections" "${temp}/ansible.egg-info/"
diff -Naur "${expected_package_dir}" "${temp}"

# Ensure package files can be regenerated
generate_tag_files "${@:3}"
rm -rf "${temp}/ansible_collections"
diff -ur "${expected_package_dir}" "${temp}"
