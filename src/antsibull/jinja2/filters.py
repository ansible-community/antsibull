# Copyright: (c) 2019, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
Jinja2 filters for use in Ansible documentation.
"""

import re
from html import escape as html_escape
from urllib.parse import quote

import typing as t

from jinja2.runtime import Undefined

from ..logging import log


mlog = log.fields(mod=__name__)

# Warning: If you add to this, then you also have to change ansible-doc
# (ansible/cli/__init__.py) in the ansible/ansible repository
_ITALIC = re.compile(r"\bI\(([^)]+)\)")
_BOLD = re.compile(r"\bB\(([^)]+)\)")
_MODULE = re.compile(r"\bM\(([^).]+)\.([^).]+)\.([^)]+)\)")
_URL = re.compile(r"\bU\(([^)]+)\)")
_LINK = re.compile(r"\bL\(([^)]+), *([^)]+)\)")
_REF = re.compile(r"\bR\(([^)]+), *([^)]+)\)")
_CONST = re.compile(r"\bC\(([^)]+)\)")
_RULER = re.compile(r"\bHORIZONTALLINE\b")

_EMAIL_ADDRESS = re.compile(r"(?:<{mail}>|\({mail}\)|{mail})".format(mail=r"[\w.+-]+@[\w.-]+\.\w+"))


def html_ify(text):
    ''' convert symbols like I(this is in italics) to valid HTML '''

    flog = mlog.fields(func='html_ify')
    flog.fields(text=text).debug('Enter')
    _counts = {}

    text = html_escape(text)
    text, _counts['italic'] = _ITALIC.subn(r"<em>\1</em>", text)
    text, _counts['bold'] = _BOLD.subn(r"<b>\1</b>", text)
    text, _counts['module'] = _MODULE.subn(
        r"<a href='../../\1/\2/\3_module.html' class='module'>\1.\2.\3</a>", text)
    text, _counts['url'] = _URL.subn(r"<a href='\1'>\1</a>", text)
    text, _counts['ref'] = _REF.subn(r"<span class='module'>\1</span>", text)
    text, _counts['link'] = _LINK.subn(r"<a href='\2'>\1</a>", text)
    text, _counts['const'] = _CONST.subn(
        r"<code class='docutils literal notranslate'>\1</code>", text)
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


def rst_ify(text):
    ''' convert symbols like I(this is in italics) to valid restructured text '''

    flog = mlog.fields(func='rst_ify')
    flog.fields(text=text).debug('Enter')
    _counts = {}

    text, _counts['italic'] = _ITALIC.subn(_rst_ify_italic, text)
    text, _counts['bold'] = _BOLD.subn(_rst_ify_bold, text)
    text, _counts['module'] = _MODULE.subn(_rst_ify_module, text)
    text, _counts['link'] = _LINK.subn(_rst_ify_link, text)
    text, _counts['url'] = _URL.subn(_rst_ify_url, text)
    text, _counts['ref'] = _REF.subn(_rst_ify_ref, text)
    text, _counts['const'] = _CONST.subn(_rst_ify_const, text)
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
