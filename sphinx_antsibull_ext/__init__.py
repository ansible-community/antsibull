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
Antsibull minimal Sphinx extension which adds some features from the Ansible doc site.
'''

from __future__ import (absolute_import, division, print_function)

__version__ = "0.1.0"
__license__ = "BSD license"
__author__ = "Felix Fontein"
__author_email__ = "felix@fontein.de"


from .pygments_lexer import AnsibleOutputLexer
from .assets import setup_assets


def setup(app):
    '''
    Initializer for Sphinx extension API.
    See http://www.sphinx-doc.org/en/stable/extdev/index.html#dev-extensions.
    '''

    # Add Pygments lexers
    for lexer in [
        AnsibleOutputLexer(startinline=True)
    ]:
        app.add_lexer(lexer.name, lexer)
        for alias in lexer.aliases:
            app.add_lexer(alias, lexer)

    # Add assets
    setup_assets(app)

    return dict(
        parallel_read_safe=True,
        parallel_write_safe=True,
        version=__version__,
    )
