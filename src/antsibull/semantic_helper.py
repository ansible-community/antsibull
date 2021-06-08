# Copyright: (c) 2021, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
Helpers for parsing semantic markup.
"""

import re

import typing as t


_ARRAY_STUB_RE = re.compile(r'\[([^\]]*)\]')
_FQCN_TYPE_PREFIX_RE = re.compile(r'^([^.]+\.[^.]+\.[^#]+)#([a-z]+):(.*)$')
_IGNORE_MARKER = 'ignore:'


def _remove_array_stubs(text: str) -> str:
    return _ARRAY_STUB_RE.sub('', text)


def parse_option(text: str, plugin_fqcn: t.Optional[str], plugin_type: t.Optional[str],
                 require_plugin=False) -> t.Tuple[str, str, str, str, t.Optional[str]]:
    """
    Given the contents of O(...) / :ansopt:`...` with potential escaping removed,
    split it into plugin FQCN, plugin type, option link name, option name, and option value.
    """
    value = None
    if '=' in text:
        text, value = text.split('=', 1)
    m = _FQCN_TYPE_PREFIX_RE.match(text)
    if m:
        plugin_fqcn = m.group(1)
        plugin_type = m.group(2)
        text = m.group(3)
    elif require_plugin:
        raise ValueError('Cannot extract plugin name and type')
    elif text.startswith(_IGNORE_MARKER):
        plugin_fqcn = ''
        plugin_type = ''
        text = text[len(_IGNORE_MARKER):]
    if ':' in text or '#' in text:
        raise ValueError(f'Invalid option name "{text}"')
    return plugin_fqcn, plugin_type, _remove_array_stubs(text), text, value


def parse_return_value(text: str, plugin_fqcn: t.Optional[str], plugin_type: t.Optional[str],
                       require_plugin=False) -> t.Tuple[str, str, str, str, t.Optional[str]]:
    """
    Given the contents of RV(...) / :ansretval:`...` with potential escaping removed,
    split it into plugin FQCN, plugin type, option link name, option name, and option value.
    """
    value = None
    if '=' in text:
        text, value = text.split('=', 1)
    m = _FQCN_TYPE_PREFIX_RE.match(text)
    if m:
        plugin_fqcn = m.group(1)
        plugin_type = m.group(2)
        text = m.group(3)
    elif require_plugin:
        raise ValueError('Cannot extract plugin name and type')
    elif text.startswith(_IGNORE_MARKER):
        plugin_fqcn = ''
        plugin_type = ''
        text = text[len(_IGNORE_MARKER):]
    if ':' in text or '#' in text:
        raise ValueError(f'Invalid return value name "{text}"')
    return plugin_fqcn, plugin_type, _remove_array_stubs(text), text, value


def augment_plugin_name_type(text: str, plugin_fqcn: t.Optional[str], plugin_type: t.Optional[str]
                             ) -> str:
    """
    Given the text contents of O(...) or RV(...) and a plugin's FQCN and type, insert
    the FQCN and type if they are not already present.
    """
    value = None
    if '=' in text:
        text, value = text.split('=', 1)
    if ':' not in text and plugin_fqcn and plugin_type:
        text = f'{plugin_fqcn}#{plugin_type}:{text}'
    return text if value is None else f'{text}={value}'
