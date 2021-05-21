# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Constant values for use throughout the antsibull codebase."""

from typing import Dict, FrozenSet


#: All the types of ansible plugins
PLUGIN_TYPES: FrozenSet[str] = frozenset(('become', 'cache', 'callback', 'cliconf', 'connection',
                                          'httpapi', 'inventory', 'lookup', 'shell', 'strategy',
                                          'vars', 'module', 'module_utils', 'role',))

#: The subset of PLUGINS which we build documentation for
DOCUMENTABLE_PLUGINS: FrozenSet[str] = frozenset(('become', 'cache', 'callback', 'cliconf',
                                                  'connection', 'httpapi', 'inventory', 'lookup',
                                                  'netconf', 'shell', 'vars', 'module',
                                                  'strategy', 'role',))


DOCUMENTABLE_PLUGINS_MIN_VERSION: Dict[str, str] = {
    'role': '2.11.0',
}
