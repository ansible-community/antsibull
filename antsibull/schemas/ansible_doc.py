# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2021

import warnings

# This module is just a backwards compatible location for ansible_doc so the wildcard
# import is just putting all the symbols from docs.ansible_doc into this namespace.
# pylint: disable=wildcard-import,unused-wildcard-import
from .docs.ansible_doc import *  # noqa: F403,F401


warnings.warn('antsibull.schemas.ansible_doc is deprecated.'
              ' Use antsibull.schemas.docs.ansible_doc instead.',
              DeprecationWarning, stacklevel=2)
