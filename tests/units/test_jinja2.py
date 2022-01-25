import pytest

from antsibull.jinja2.filters import rst_ify, rst_escape, move_first, massage_author_name


RST_IFY_DATA = {
    # No substitutions
    'no-op': 'no-op',
    'no-op Z(test)': 'no-op Z(test)',
    # Simple cases of all substitutions
    'I(italic)': r'\ :emphasis:`italic`\ ',
    'B(bold)': r'\ :strong:`bold`\ ',
    'M(ansible.builtin.yum)': r'\ :ref:`ansible.builtin.yum'
    r' <ansible_collections.ansible.builtin.yum_module>`\ ',
    'U(https://docs.ansible.com)': r'\ https://docs.ansible.com\ ',
    'L(the user guide,https://docs.ansible.com/user-guide.html)': r'\ `the user guide'
    r' <https://docs.ansible.com/user-guide.html>`__\ ',
    'R(the user guide,user-guide)': r'\ :ref:`the user guide <user-guide>`\ ',
    'C(/usr/bin/file)': r'\ :literal:`/usr/bin/file`\ ',
    'HORIZONTALLINE': '\n\n.. raw:: html\n\n  <hr>\n\n',
    # Multiple substitutions
    'The M(ansible.builtin.yum) module B(MUST) be given the C(package) parameter.  See the R(looping docs,using-loops) for more info':
    r'The \ :ref:`ansible.builtin.yum <ansible_collections.ansible.builtin.yum_module>`\  module \ :strong:`MUST`\  be given the \ :literal:`package`\  parameter.  See the \ :ref:`looping docs <using-loops>`\  for more info',
    # Problem cases
    'IBM(International Business Machines)': 'IBM(International Business Machines)',
    'L(the user guide, https://docs.ansible.com/)': r'\ `the user guide <https://docs.ansible.com/>`__\ ',
    'R(the user guide, user-guide)': r'\ :ref:`the user guide <user-guide>`\ ',
}


@pytest.mark.parametrize('text, expected', RST_IFY_DATA.items())
def test_rst_ify(text, expected):
    assert rst_ify(text) == expected


RST_ESCAPE_DATA = {
    '': '',
    'no-op': 'no-op',
    None: 'None',
    1: '1',
    '*': '\\*',
    '_': '\\_',
    '<': '\\<',
    '>': '\\>',
    '`': '\\`',
    '\\': '\\\\',
    '\\*': '\\\\\\*',
    '*\\': '\\*\\\\',
    ':role:`test`': ':role:\\`test\\`',
}


@pytest.mark.parametrize('value, expected', RST_ESCAPE_DATA.items())
def test_escape_ify(value, expected):
    assert rst_escape(value) == expected


MOVE_FIRST_DATA = [
    ([], [], []),
    (['a', 'b', 'c'], ['d'], ['a', 'b', 'c']),
    (['a', 'b', 'c'], ['b'], ['b', 'a', 'c']),
    (['a', 'b', 'b', 'c'], ['b'], ['b', 'a', 'b', 'c']),
    (['a', 'b', 'c'], ['b', 'c'], ['b', 'c', 'a']),
    (['a', 'b', 'c'], ['c', 'b'], ['c', 'b', 'a']),
]


@pytest.mark.parametrize('input, move_to_beginning, expected', MOVE_FIRST_DATA)
def test_move_first(input, move_to_beginning, expected):
    assert move_first(input, *move_to_beginning) == expected


MASSAGE_AUTHOR_NAME = [
    ('', ''),
    ('John Doe (@johndoe) <john.doe@gmail.com>', 'John Doe (@johndoe) '),
    ('John Doe (@johndoe) john+doe@gmail.com', 'John Doe (@johndoe) '),
    ('John Doe (@johndoe) (john-doe@gmail.com)', 'John Doe (@johndoe) '),
    ('John Doe (@johndoe, john.doe@gmail.com)', 'John Doe (@johndoe, )'),
]


@pytest.mark.parametrize('input, expected', MASSAGE_AUTHOR_NAME)
def test_massage_author_name(input, expected):
    assert massage_author_name(input) == expected
