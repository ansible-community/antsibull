# Copyright: (c) 2019, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
Jinja2 filters for use in Ansible documentation.
"""

import re
from html import escape as html_escape

from jinja2.runtime import Undefined


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

    text = html_escape(text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _MODULE.sub(r"<span class='module'>\1</span>", text)
    text = _URL.sub(r"<a href='\1'>\1</a>", text)
    text = _REF.sub(r"<span class='module'>\1</span>", text)
    text = _LINK.sub(r"<a href='\2'>\1</a>", text)
    text = _CONST.sub(r"<code>\1</code>", text)
    text = _RULER.sub(r"<hr/>", text)

    return text.strip()


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

    text = _ITALIC.sub(r"*\1*", text)
    text = _BOLD.sub(r"**\1**", text)
    text = _MODULE.sub(r":ref:`\1 <ansible_collections.\1_module>`", text)
    text = _LINK.sub(r"`\1 <\2>`_", text)
    text = _URL.sub(r"\1", text)
    text = _REF.sub(r":ref:`\1 <\2>`", text)
    text = _CONST.sub(r"``\1``", text)
    text = _RULER.sub(f"\n\n{'-' * 13}\n\n", text)

    return text


def rst_fmt(text, fmt):
    ''' helper for Jinja2 to do format strings '''

    return fmt % (text)


def rst_xline(width, char="="):
    ''' return a restructured text line of a given length '''

    return char * width
