#!/usr/bin/bash -x
# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

set -euo pipefail

version="${1}"
directory="${2-.}"
topdir="ansible-${version}"
url=https://files.pythonhosted.org/packages/source/a/ansible/${topdir}.tar.gz

cd "${directory}"
if [ -f "${topdir}.tar.gz" ]; then
    exit
fi
wget "${url}"
