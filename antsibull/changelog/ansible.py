# -*- coding: utf-8 -*-
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Return Ansible-specific information, like current release or list of documentable plugins.
"""

from typing import Tuple

try:
    from ansible import constants as C
    HAS_ANSIBLE_CONSTANTS = True
except ImportError:
    HAS_ANSIBLE_CONSTANTS = False


try:
    from ansible import release as ansible_release
    HAS_ANSIBLE_RELEASE = True
except ImportError:
    HAS_ANSIBLE_RELEASE = False


def get_documentable_plugins() -> Tuple[str, ...]:
    """
    Retrieve plugin types that can be documented. Does not include 'module'.
    """
    if HAS_ANSIBLE_CONSTANTS:
        return C.DOCUMENTABLE_PLUGINS
    return (
        'become', 'cache', 'callback', 'cliconf', 'connection', 'httpapi', 'inventory',
        'lookup', 'netconf', 'shell', 'vars', 'module', 'strategy',
    )


def get_ansible_release() -> Tuple[str, str]:
    """
    Retrieve current version and codename of Ansible.

    :return: Tuple with version and codename
    """
    if not HAS_ANSIBLE_RELEASE:
        raise ValueError('Cannot import ansible.release')
    return ansible_release.__version__, ansible_release.__codename__
