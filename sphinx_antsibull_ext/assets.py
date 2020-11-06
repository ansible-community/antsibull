# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020
'''
Handling assets.
'''

from __future__ import (absolute_import, division, print_function)


import os

from pkg_resources import resource_filename

from sphinx.util.fileutil import copy_asset


CSS_FILES = [
    'antsibull-minimal.css',
]


def _copy_asset_files(app, exc):  # pylint: disable=unused-argument
    '''
    Copy asset files.
    '''
    # Copy CSS files
    for file in CSS_FILES:
        source = resource_filename(__name__, file)
        destination = os.path.join(app.outdir, '_static')
        copy_asset(source, destination)


def setup_assets(app):
    '''
    Setup assets for a Sphinx app object.
    '''
    # Copy assets
    app.connect('build-finished', _copy_asset_files)

    # Add CSS files
    for file in CSS_FILES:
        app.add_css_file(file)
