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


from .pygments_lexer import AnsibleOutputLexer
from .assets import setup_assets


def setup(app):
    '''
    Initializer for Sphinx extension API.
    See http://www.sphinx-doc.org/en/stable/extdev/index.html#dev-extensions.
    '''

    # Add Pygments lexers
    for lexer in [
        AnsibleOutputLexer
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
