# -*- coding: utf-8 -*-
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Return Ansible-specific information, like current release or list of documentable plugins.
"""

try:
    from ansible import constants as C  # pyre-ignore
    HAS_ANSIBLE_CONSTANTS = True
except ImportError:
    HAS_ANSIBLE_CONSTANTS = False


try:
    from ansible import release as ansible_release
    HAS_ANSIBLE_RELEASE = True
except ImportError:
    HAS_ANSIBLE_RELEASE = False


def get_documentable_plugins():
    """ Retrieve plugin types that can be documented. Does not include 'module'.
    :rtype tuple[str]:
    """
    if HAS_ANSIBLE_CONSTANTS is not None:
        return C.DOCUMENTABLE_PLUGINS
    return (
        'become', 'cache', 'callback', 'cliconf', 'connection', 'httpapi', 'inventory',
        'lookup', 'netconf', 'shell', 'vars', 'module', 'strategy',
    )


def get_ansible_release():
    """Retrieve current version and codename of Ansible.
    :rtype (str, str): version and codename
    """
    if not HAS_ANSIBLE_RELEASE:
        raise ValueError('Cannot import ansible.release')
    return ansible_release.__version__, ansible_release.__codename__
