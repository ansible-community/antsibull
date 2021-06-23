# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2021
'''
Add roles for semantic markup.
'''

from __future__ import (absolute_import, division, print_function)


from docutils import nodes


def option_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """Format Ansible option key, or option key-value.

    Returns 2 part tuple containing list of nodes to insert into the
    document and a list of system messages.  Both are allowed to be
    empty.

    :param name: The role name used in the document.
    :param rawtext: The entire markup snippet, with role.
    :param text: The text marked with the role.
    :param lineno: The line number where rawtext appears in the input.
    :param inliner: The inliner instance that called us.
    :param options: Directive options for customization.
    :param content: The directive content for customization.
    """
    children = []
    classes = []
    if '=' not in text and ':' not in text:
        children.append(nodes.strong(rawtext, text))
        rawtext = ''
        text = ''
        classes.append('ansible-option')
    else:
        classes.append('ansible-option-value')
    return [nodes.literal(rawtext, text, *children, classes=classes)], []


def value_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """Format Ansible option value.

    Returns 2 part tuple containing list of nodes to insert into the
    document and a list of system messages.  Both are allowed to be
    empty.

    :param name: The role name used in the document.
    :param rawtext: The entire markup snippet, with role.
    :param text: The text marked with the role.
    :param lineno: The line number where rawtext appears in the input.
    :param inliner: The inliner instance that called us.
    :param options: Directive options for customization.
    :param content: The directive content for customization.
    """
    return [nodes.literal(rawtext, text, classes=['ansible-value'])], []


ROLES = {
    'ansopt': option_role,
    'ansval': value_role,
}


def setup_roles(app):
    '''
    Setup roles for a Sphinx app object.
    '''
    for name, role in ROLES.items():
        app.add_role(name, role)
