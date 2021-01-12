# Copyright: (c) 2019, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
Jinja2 filters for use in Ansible documentation.
"""

import re
from html import escape as html_escape

from jinja2.runtime import Undefined

from ..logging import log


mlog = log.fields(mod=__name__)

# Warning: If you add to this, then you also have to change ansible-doc
# (ansible/cli/__init__.py) in the ansible/ansible repository
_ITALIC = re.compile(r"\bI\(([^)]+)\)")
_BOLD = re.compile(r"\bB\(([^)]+)\)")
_MODULE = re.compile(r"\bM\(([^)]+)\)")
_URL = re.compile(r"\bU\(([^)]+)\)")
_LINK = re.compile(r"\bL\(([^)]+), *([^)]+)\)")
_REF = re.compile(r"\bR\(([^)]+), *([^)]+)\)")
_CONST = re.compile(r"\bC\(([^)]+)\)")
_RULER = re.compile(r"\bHORIZONTALLINE\b")


def html_ify(text):
    ''' convert symbols like I(this is in italics) to valid HTML '''

    flog = mlog.fields(func='html_ify')
    flog.fields(text=text).debug('Enter')
    _counts = {}

    text = html_escape(text)
    text, _counts['italic'] = _ITALIC.subn(r"<em>\1</em>", text)
    text, _counts['bold'] = _BOLD.subn(r"<b>\1</b>", text)
    text, _counts['module'] = _MODULE.subn(r"<span class='module'>\1</span>", text)
    text, _counts['url'] = _URL.subn(r"<a href='\1'>\1</a>", text)
    text, _counts['ref'] = _REF.subn(r"<span class='module'>\1</span>", text)
    text, _counts['link'] = _LINK.subn(r"<a href='\2'>\1</a>", text)
    text, _counts['const'] = _CONST.subn(r"<code>\1</code>", text)
    text, _counts['ruler'] = _RULER.subn(r"<hr/>", text)

    text = text.strip()
    flog.fields(counts=_counts).info('Number of macros converted to html equivalents')
    flog.debug('Leave')
    return text


def documented_type(text):
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


def rst_ify(text):
    ''' convert symbols like I(this is in italics) to valid restructured text '''

    flog = mlog.fields(func='html_ify')
    flog.fields(text=text).debug('Enter')
    _counts = {}

    text, _counts['italic'] = _ITALIC.subn(r"*\1*", text)
    text, _counts['bold'] = _BOLD.subn(r"**\1**", text)
    text, _counts['module'] = _MODULE.subn(r":ref:`\1 <ansible_collections.\1_module>`", text)
    text, _counts['url'] = _LINK.subn(r"`\1 <\2>`_", text)
    text, _counts['ref'] = _URL.subn(r"\1", text)
    text, _counts['link'] = _REF.subn(r":ref:`\1 <\2>`", text)
    text, _counts['const'] = _CONST.subn(r"``\1``", text)
    text, _counts['ruler'] = _RULER.subn(f"\n\n{'-' * 13}\n\n", text)

    flog.fields(counts=_counts).info('Number of macros converted to rst equivalents')
    flog.debug('Leave')
    return text


def rst_fmt(text, fmt):
    ''' helper for Jinja2 to do format strings '''

    return fmt % (text)


def rst_xline(width, char="="):
    ''' return a restructured text line of a given length '''

    return char * width
