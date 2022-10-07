# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.module_utils.common.text.converters import to_native


def parse_deps(content):
    decoded_contents = to_native(content)
    lines = [
        line.strip() for line in decoded_contents.split('\n')
        if line.strip() and not line.strip().startswith('#')
    ]
    deps = {}
    for line in lines:
        record = [entry.strip() for entry in line.split(':', 1)]
        deps[record[0]] = record[1]
    return deps


class FilterModule(object):
    ''' Deps file parsing filters '''

    def filters(self):
        filters = {
            '_antsibull_parse_deps': parse_deps,
        }

        return filters
