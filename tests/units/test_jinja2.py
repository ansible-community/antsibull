import pytest

from antsibull.jinja2.filters import rst_ify


RST_IFY_DATA = {
    # No substitutions
    'no-op': 'no-op',
    'no-op Z(test)': 'no-op Z(test)',
    # Simple cases of all substitutions
    'I(italic)': '*italic*',
    'B(bold)': '**bold**',
    'M(ansible.builtin.yum)': ':ref:`ansible.builtin.yum'
    ' <ansible_collections.ansible.builtin.yum_module>`',
    'U(https://docs.ansible.com)': 'https://docs.ansible.com',
    'L(the user guide,https://docs.ansible.com/user-guide.html)': '`the user guide'
    ' <https://docs.ansible.com/user-guide.html>`_',
    'R(the user guide,user-guide)': ':ref:`the user guide <user-guide>`',
    'C(/usr/bin/file)': '``/usr/bin/file``',
    'HORIZONTALLINE': '\n\n{0}\n\n'.format('-' * 13),
    # Multiple substitutions
    'The M(ansible.builtin.yum) module B(MUST) be given the C(package) parameter.  See the R(looping docs,using-loops) for more info':
    'The :ref:`ansible.builtin.yum <ansible_collections.ansible.builtin.yum_module>` module **MUST** be given the ``package`` parameter.  See the :ref:`looping docs <using-loops>` for more info',
    # Problem cases
    'IBM(International Business Machines)': 'IBM(International Business Machines)',
    'L(the user guide, https://docs.ansible.com/)': '`the user guide <https://docs.ansible.com/>`_',
    'R(the user guide, user-guide)': ':ref:`the user guide <user-guide>`',
}


@pytest.mark.parametrize('text, expected', RST_IFY_DATA.items())
def test_rst_ify(text, expected):
    assert rst_ify(text) == expected
