# -*- coding: utf-8 -*-
#
# Copyright 2020 by Felix Fontein
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
