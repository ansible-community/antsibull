# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020
'''
Antsibull minimal Sphinx extension which adds some features from the Ansible doc site.
'''

from __future__ import (absolute_import, division, print_function)

__version__ = "0.1.1"
__license__ = "BSD license"
__author__ = "Felix Fontein"
__author_email__ = "felix@fontein.de"


from .assets import setup_assets
from .roles import setup_roles


def setup(app):
    '''
    Initializer for Sphinx extension API.
    See http://www.sphinx-doc.org/en/stable/extdev/index.html#dev-extensions.
    '''

    # Add assets
    setup_assets(app)

    # Add roles
    setup_roles(app)

    return dict(
        parallel_read_safe=True,
        parallel_write_safe=True,
        version=__version__,
    )
