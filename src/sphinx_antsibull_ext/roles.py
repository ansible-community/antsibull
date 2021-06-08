# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2021
'''
Add roles for semantic markup.
'''

import typing as t

from docutils import nodes
from sphinx import addnodes

from antsibull.semantic_helper import parse_option, parse_return_value


def _create_option_reference(plugin_fqcn: str, plugin_type: str, option: str) -> t.Optional[str]:
    if not plugin_fqcn or not plugin_type:
        return None
    # TODO: handle role arguments (entrypoint!)
    ref = option.replace(".", "/")
    return f'ansible_collections.{plugin_fqcn}_{plugin_type}__parameter-{ref}'


def _create_return_value_reference(plugin_fqcn: str, plugin_type: str, return_value: str
                                   ) -> t.Optional[str]:
    if not plugin_fqcn or not plugin_type:
        return None
    ref = return_value.replace(".", "/")
    return f'ansible_collections.{plugin_fqcn}_{plugin_type}__return-{ref}'


def _create_ref_or_not(create_ref: t.Callable[[str, str, str], t.Optional[str]],
                       plugin_fqcn: str, plugin_type: str, ref_parameter: str,
                       text: str) -> t.Tuple[str, t.List[t.Any]]:
    ref = create_ref(plugin_fqcn, plugin_type, ref_parameter)
    if ref is None:
        return text, []

    # The content node will be replaced by Sphinx anyway, so it doesn't matter what kind
    # of node we are using...
    content = nodes.literal(text, text)

    options = {
        'reftype': 'ref',
        'refdomain': 'std',
        'refexplicit': True,
        'refwarn': True,
    }
    refnode = addnodes.pending_xref(text, content, **options)  # pyre-ignore[19]
    refnode['reftarget'] = ref  # pyre-ignore[16]
    return '', [refnode]


# pylint:disable-next=unused-argument
def _create_error(rawtext: str, text: str, error: str) -> t.Tuple[t.List[t.Any], t.List[str]]:
    node = ...  # FIXME
    return [node], []


# pylint:disable-next=unused-argument,dangerous-default-value
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
    classes = []
    try:
        plugin_fqcn, plugin_type, option_link, option, value = parse_option(
            text.replace('\x00', ''), '', '', require_plugin=False)
    except ValueError as exc:
        return _create_error(rawtext, text, str(exc))
    if value is None:
        text = f'{option}'
        classes.append('ansible-option')
    else:
        text = f'{option}={value}'
        classes.append('ansible-option-value')
    text, subnodes = _create_ref_or_not(
        _create_option_reference, plugin_fqcn, plugin_type, option_link, text)
    if value is None:
        content = nodes.strong(rawtext, text, *subnodes)
        content = nodes.literal(rawtext, '', content, classes=classes)
    else:
        content = nodes.literal(rawtext, text, *subnodes, classes=classes)
    return [content], []


# pylint:disable-next=unused-argument,dangerous-default-value
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


# pylint:disable-next=unused-argument,dangerous-default-value
def return_value_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
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
    classes = ['ansible-return-value']
    try:
        plugin_fqcn, plugin_type, rv_link, rv, value = parse_return_value(
            text.replace('\x00', ''), '', '', require_plugin=False)
    except ValueError as exc:
        return _create_error(rawtext, text, str(exc))
    if value is None:
        text = f'{rv}'
    else:
        text = f'{rv}={value}'
    text, subnodes = _create_ref_or_not(
        _create_return_value_reference, plugin_fqcn, plugin_type, rv_link, text)
    return [nodes.literal(rawtext, text, *subnodes, classes=classes)], []


ROLES = {
    'ansopt': option_role,
    'ansval': value_role,
    'ansretval': return_value_role,
}


def setup_roles(app):
    '''
    Setup roles for a Sphinx app object.
    '''
    for name, role in ROLES.items():
        app.add_role(name, role)
