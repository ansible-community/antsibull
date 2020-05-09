# -*- coding: utf-8 -*-
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


try:
    from ansible import constants as C  # pyre-ignore
except ImportError:
    C = None


try:
    from ansible import release as ansible_release
    ansible_release_import_error = None
except ImportError as e:
    ansible_release = None
    ansible_release_import_error = e


def get_documentable_plugins():
    """ Retrieve plugin types that can be documented. Does not include 'module'.
    :rtype tuple[str]:
    """
    if C is not None:
        return C.DOCUMENTABLE_PLUGINS
    return (
        'become', 'cache', 'callback', 'cliconf', 'connection', 'httpapi', 'inventory',
        'lookup', 'netconf', 'shell', 'vars', 'module', 'strategy',
    )


def get_ansible_release():
    """Retrieve current version and codename of Ansible.
    :rtype (str, str): version and codename
    """
    if ansible_release is None:
        raise ansible_release_import_error
    return ansible_release.__version__, ansible_release.__codename__
