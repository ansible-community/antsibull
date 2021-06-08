# Copyright: (c) 2019, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
Jinja2 filters for use in Ansible documentation.
"""

import re
from functools import partial
from html import escape as html_escape
from urllib.parse import quote

import typing as t

from jinja2.runtime import Context, Undefined
from jinja2.utils import pass_context

from ..logging import log
from ..semantic_helper import parse_option, parse_return_value, augment_plugin_name_type


mlog = log.fields(mod=__name__)

# Warning: If you add to this, then you also have to change ansible-doc
# (ansible/cli/__init__.py) in the ansible/ansible repository
_ITALIC = re.compile(r"\bI\(([^)]+)\)")
_BOLD = re.compile(r"\bB\(([^)]+)\)")
_MODULE = re.compile(r"\bM\(([^).]+)\.([^).]+)\.([^)]+)\)")
_PLUGIN = re.compile(r"\bP\(([^).]+)\.([^).]+)\.([^)]+)#([a-z]+)\)")
_URL = re.compile(r"\bU\(([^)]+)\)")
_LINK = re.compile(r"\bL\(([^)]+), *([^)]+)\)")
_REF = re.compile(r"\bR\(([^)]+), *([^)]+)\)")
_CONST = re.compile(r"\bC\(([^)]+)\)")
_SEM_PARAMETER_STRING = r"\(((?:[^\\)]+|\\.)+)\)"
_SEM_OPTION_NAME = re.compile(r"\bO" + _SEM_PARAMETER_STRING)
_SEM_OPTION_VALUE = re.compile(r"\bV" + _SEM_PARAMETER_STRING)
_SEM_ENV_VARIABLE = re.compile(r"\bE" + _SEM_PARAMETER_STRING)
_SEM_RET_VALUE = re.compile(r"\bRV" + _SEM_PARAMETER_STRING)
_RULER = re.compile(r"\bHORIZONTALLINE\b")
_UNESCAPE = re.compile(r"\\(.)")

_EMAIL_ADDRESS = re.compile(r"(?:<{mail}>|\({mail}\)|{mail})".format(mail=r"[\w.+-]+@[\w.-]+\.\w+"))


def extract_plugin_data(context: Context) -> t.Tuple[t.Optional[str], t.Optional[str]]:
    plugin_fqcn = context.get('plugin_name')
    plugin_type = context.get('plugin_type')
    if plugin_fqcn is None or plugin_type is None:
        return None, None
    # if plugin_type == 'role':
    #     entry_point = context.get('entry_point', 'main')
    #     # FIXME: use entry_point
    return plugin_fqcn, plugin_type


def _unescape_sem_value(text: str) -> str:
    return _UNESCAPE.sub(r'\1', text)


def _check_plugin(plugin_fqcn: t.Optional[str], plugin_type: t.Optional[str],
                  matcher: 're.Match') -> None:
    if plugin_fqcn is None or plugin_type is None:
        raise Exception(f'The markup {matcher.group(0)} cannot be used outside a plugin or role')


def _create_error(text: str, error: str) -> str:  # pylint:disable=unused-argument
    return '...'  # FIXME


def _option_name_html(plugin_fqcn: t.Optional[str], plugin_type: t.Optional[str],
                      matcher: 're.Match') -> str:
    _check_plugin(plugin_fqcn, plugin_type, matcher)
    text = _unescape_sem_value(matcher.group(1))
    try:
        plugin_fqcn, plugin_type, option_link, option, value = parse_option(
            text, plugin_fqcn, plugin_type, require_plugin=False)
    except ValueError as exc:
        return _create_error(text, str(exc))
    if value is None:
        cls = 'ansible-option'
        text = f'{option}'
        strong_start = '<strong>'
        strong_end = '</strong>'
    else:
        cls = 'ansible-option-value'
        text = f'{option}={value}'
        strong_start = ''
        strong_end = ''
    if plugin_fqcn and plugin_type and plugin_fqcn.count('.') >= 2:
        # TODO: handle role arguments (entrypoint!)
        namespace, name, plugin = plugin_fqcn.split('.', 2)
        url = f'../../{namespace}/{name}/{plugin}_{plugin_type}.html'
        fragment = f'parameter-{option_link.replace(".", "/")}'
        link_start = (
            f'<a class="reference internal" href="{url}#{fragment}">'
            '<span class="std std-ref"><span class="pre">'
        )
        link_end = '</span></span></a>'
    else:
        link_start = ''
        link_end = ''
    return (
        f'<code class="{cls} literal notranslate">'
        f'{strong_start}{link_start}{text}{link_end}{strong_end}</code>'
    )


def _return_value_html(plugin_fqcn: t.Optional[str], plugin_type: t.Optional[str],
                       matcher: 're.Match') -> str:
    _check_plugin(plugin_fqcn, plugin_type, matcher)
    text = _unescape_sem_value(matcher.group(1))
    try:
        plugin_fqcn, plugin_type, rv_link, rv, value = parse_return_value(
            text, plugin_fqcn, plugin_type, require_plugin=False)
    except ValueError as exc:
        return _create_error(text, str(exc))
    cls = 'ansible-return-value'
    if value is None:
        text = f'{rv}'
    else:
        text = f'{rv}={value}'
    if plugin_fqcn and plugin_type and plugin_fqcn.count('.') >= 2:
        namespace, name, plugin = plugin_fqcn.split('.', 2)
        url = f'../../{namespace}/{name}/{plugin}_{plugin_type}.html'
        fragment = f'return-{rv_link.replace(".", "/")}'
        link_start = (
            f'<a class="reference internal" href="{url}#{fragment}">'
            '<span class="std std-ref"><span class="pre">'
        )
        link_end = '</span></span></a>'
    else:
        link_start = ''
        link_end = ''
    return f'<code class="{cls} literal notranslate">{link_start}{text}{link_end}</code>'


def _value_html(matcher: 're.Match') -> str:
    text = _unescape_sem_value(matcher.group(1))
    return f'<code class="ansible-value literal notranslate">{text}</code>'


def _env_var_html(matcher: 're.Match') -> str:
    text = _unescape_sem_value(matcher.group(1))
    return f'<code class="xref std std-envvar literal notranslate">{text}</code>'


@pass_context
def html_ify(context: Context, text: str) -> str:
    ''' convert symbols like I(this is in italics) to valid HTML '''

    flog = mlog.fields(func='html_ify')
    flog.fields(text=text).debug('Enter')
    _counts = {}

    plugin_fqcn, plugin_type = extract_plugin_data(context)

    text = html_escape(text)
    text, _counts['italic'] = _ITALIC.subn(r"<em>\1</em>", text)
    text, _counts['bold'] = _BOLD.subn(r"<b>\1</b>", text)
    text, _counts['module'] = _MODULE.subn(
        r"<a href='../../\1/\2/\3_module.html' class='module'>\1.\2.\3</a>", text)
    text, _counts['plugin'] = _PLUGIN.subn(
        r"<a href='../../\1/\2/\3_\4.html' class='module plugin-\4'>\1.\2.\3</span>", text)
    text, _counts['url'] = _URL.subn(r"<a href='\1'>\1</a>", text)
    text, _counts['ref'] = _REF.subn(r"<span class='module'>\1</span>", text)
    text, _counts['link'] = _LINK.subn(r"<a href='\2'>\1</a>", text)
    text, _counts['const'] = _CONST.subn(
        r"<code class='docutils literal notranslate'>\1</code>", text)
    text, _counts['option-name'] = _SEM_OPTION_NAME.subn(
        partial(_option_name_html, plugin_fqcn, plugin_type), text)
    text, _counts['option-value'] = _SEM_OPTION_VALUE.subn(_value_html, text)
    text, _counts['environment-var'] = _SEM_ENV_VARIABLE.subn(_env_var_html, text)
    text, _counts['return-value'] = _SEM_RET_VALUE.subn(
        partial(_return_value_html, plugin_fqcn, plugin_type), text)
    text, _counts['ruler'] = _RULER.subn(r"<hr/>", text)

    text = text.strip()
    flog.fields(counts=_counts).info('Number of macros converted to html equivalents')
    flog.debug('Leave')
    return text


def documented_type(text) -> str:
    ''' Convert any python type to a type for documentation '''

    if isinstance(text, Undefined):
        return '-'
    if text == 'str':
        return 'string'
    if text == 'bool':
        return 'boolean'
    if text == 'int':
        return 'integer'
    if text == 'dict':
        return 'dictionary'
    return text


# The max filter was added in Jinja2-2.10.  Until we can require that version, use this
def do_max(seq):
    return max(seq)


# In the following, we make heavy use of escaped whitespace ("\ ") being removed from the output.
# See
# https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#character-level-inline-markup-1
# for further information.

def _rst_ify_italic(m: 're.Match') -> str:
    return f"\\ :emphasis:`{rst_escape(m.group(1), escape_ending_whitespace=True)}`\\ "


def _rst_ify_bold(m: 're.Match') -> str:
    return f"\\ :strong:`{rst_escape(m.group(1), escape_ending_whitespace=True)}`\\ "


def _rst_ify_module(m: 're.Match') -> str:
    fqcn = f'{m.group(1)}.{m.group(2)}.{m.group(3)}'
    return f"\\ :ref:`{rst_escape(fqcn)} <ansible_collections.{fqcn}_module>`\\ "


def _rst_ify_plugin(m: 're.Match') -> str:
    fqcn = f'{m.group(1)}.{m.group(2)}.{m.group(3)}'
    plugin_type = m.group(4)
    return f"\\ :ref:`{rst_escape(fqcn)} <ansible_collections.{fqcn}_{plugin_type}>`\\ "


def _escape_url(url: str) -> str:
    # We include '<>[]{}' in safe to allow urls such as 'https://<HOST>:[PORT]/v{version}/' to
    # remain unmangled by percent encoding
    return quote(url, safe=':/#?%<>[]{}')


def _rst_ify_link(m: 're.Match') -> str:
    return f"\\ `{rst_escape(m.group(1))} <{_escape_url(m.group(2))}>`__\\ "


def _rst_ify_url(m: 're.Match') -> str:
    return f"\\ {_escape_url(m.group(1))}\\ "


def _rst_ify_ref(m: 're.Match') -> str:
    return f"\\ :ref:`{rst_escape(m.group(1))} <{m.group(2)}>`\\ "


def _rst_ify_const(m: 're.Match') -> str:
    # Escaping does not work in double backticks, so we use the :literal: role instead
    return f"\\ :literal:`{rst_escape(m.group(1), escape_ending_whitespace=True)}`\\ "


def _rst_ify_option_name(plugin_fqcn: t.Optional[str], plugin_type: t.Optional[str],
                         m: 're.Match') -> str:
    _check_plugin(plugin_fqcn, plugin_type, m)
    text = _unescape_sem_value(m.group(1))
    text = augment_plugin_name_type(text, plugin_fqcn, plugin_type)
    return f"\\ :ansopt:`{rst_escape(text, escape_ending_whitespace=True)}`\\ "


def _rst_ify_value(m: 're.Match') -> str:
    text = _unescape_sem_value(m.group(1))
    return f"\\ :ansval:`{rst_escape(text, escape_ending_whitespace=True)}`\\ "


def _rst_ify_return_value(plugin_fqcn: t.Optional[str], plugin_type: t.Optional[str],
                          m: 're.Match') -> str:
    _check_plugin(plugin_fqcn, plugin_type, m)
    text = _unescape_sem_value(m.group(1))
    text = augment_plugin_name_type(text, plugin_fqcn, plugin_type)
    return f"\\ :ansretval:`{rst_escape(text, escape_ending_whitespace=True)}`\\ "


def _rst_ify_envvar(m: 're.Match') -> str:
    text = _unescape_sem_value(m.group(1))
    return f"\\ :envvar:`{rst_escape(text, escape_ending_whitespace=True)}`\\ "


@pass_context
def rst_ify(context: Context, text: str) -> str:
    ''' convert symbols like I(this is in italics) to valid restructured text '''

    flog = mlog.fields(func='rst_ify')
    flog.fields(text=text).debug('Enter')
    _counts = {}

    plugin_fqcn, plugin_type = extract_plugin_data(context)

    text, _counts['italic'] = _ITALIC.subn(_rst_ify_italic, text)
    text, _counts['bold'] = _BOLD.subn(_rst_ify_bold, text)
    text, _counts['module'] = _MODULE.subn(_rst_ify_module, text)
    text, _counts['plugin'] = _PLUGIN.subn(_rst_ify_plugin, text)
    text, _counts['link'] = _LINK.subn(_rst_ify_link, text)
    text, _counts['url'] = _URL.subn(_rst_ify_url, text)
    text, _counts['ref'] = _REF.subn(_rst_ify_ref, text)
    text, _counts['const'] = _CONST.subn(_rst_ify_const, text)
    text, _counts['option-name'] = _SEM_OPTION_NAME.subn(
        partial(_rst_ify_option_name, plugin_fqcn, plugin_type), text)
    text, _counts['option-value'] = _SEM_OPTION_VALUE.subn(_rst_ify_value, text)
    text, _counts['environment-var'] = _SEM_ENV_VARIABLE.subn(_rst_ify_envvar, text)
    text, _counts['return-value'] = _SEM_RET_VALUE.subn(
        partial(_rst_ify_return_value, plugin_fqcn, plugin_type), text)
    text, _counts['ruler'] = _RULER.subn('\n\n.. raw:: html\n\n  <hr>\n\n', text)

    flog.fields(counts=_counts).info('Number of macros converted to rst equivalents')
    flog.debug('Leave')
    return text


def rst_escape(value: t.Any, escape_ending_whitespace=False) -> str:
    ''' make sure value is converted to a string, and RST special characters are escaped '''

    if not isinstance(value, str):
        value = str(value)

    value = value.replace('\\', '\\\\')
    value = value.replace('<', '\\<')
    value = value.replace('>', '\\>')
    value = value.replace('_', '\\_')
    value = value.replace('*', '\\*')
    value = value.replace('`', '\\`')

    if escape_ending_whitespace and value.endswith(' '):
        value = value + '\\ '
    if escape_ending_whitespace and value.startswith(' '):
        value = '\\ ' + value

    return value


def rst_fmt(text, fmt):
    ''' helper for Jinja2 to do format strings '''

    return fmt % (text)


def rst_xline(width, char="="):
    ''' return a restructured text line of a given length '''

    return char * width


def move_first(sequence, *move_to_beginning):
    ''' return a copy of sequence where the elements which are in move_to_beginning are
        moved to its beginning if they appear in the list '''

    remaining = list(sequence)
    beginning = []
    for elt in move_to_beginning:
        try:
            remaining.remove(elt)
            beginning.append(elt)
        except ValueError:
            # elt not found in remaining
            pass

    return beginning + remaining


def massage_author_name(value):
    ''' remove email addresses from the given string, and remove `(!UNKNOWN)` '''
    value = _EMAIL_ADDRESS.sub('', value)
    value = value.replace('(!UNKNOWN)', '')
    return value
