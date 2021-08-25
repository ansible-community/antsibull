# coding: utf-8
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2021
'''
Add useful directives.
'''

from __future__ import (absolute_import, division, print_function)


from docutils import nodes
from docutils.parsers.rst import Directive


class DetailsDirective(Directive):  # pyre-ignore[11]
    """Details directive.

    Creates a HTML <details> element with an optional <summary>.
    """

    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}
    has_content = True

    def run(self):
        self.assert_has_content()
        admonition_node = nodes.container(rawsource='\n'.join(self.content))
        summary_nodes = []
        if self.arguments:
            title_text = self.arguments[0]
            summary_nodes, messages = self.state.inline_text(title_text, self.lineno)

        # Parse the directive contents.
        self.state.nested_parse(self.content, self.content_offset, admonition_node)
        result = [
            nodes.raw('', '<details>', format='html'),
        ]
        if summary_nodes:
            result.append(nodes.raw('', '<summary>', format='html'))
            result.extend(summary_nodes)
            result.append(nodes.raw('', '</summary>', format='html'))
        result.extend([
            admonition_node,
            nodes.raw('', '</details>', format='html'),
        ])
        return result


DIRECTIVES = {
    'ansible-details': DetailsDirective,
}


def setup_directives(app):
    '''
    Setup directives for a Sphinx app object.
    '''
    for name, directive in DIRECTIVES.items():
        app.add_directive(name, directive)
