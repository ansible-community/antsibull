# -*- coding: utf-8 -*-
# Author: Matt Clay <matt@mystile.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020


class RstBuilder:
    """Simple RST builder."""
    def __init__(self):
        self.lines = []
        self.section_underlines = '''=-~^.*+:`'"_#'''

    def set_title(self, title):
        """Set the title.
        :type title: str
        """
        self.lines.append(self.section_underlines[0] * len(title))
        self.lines.append(title)
        self.lines.append(self.section_underlines[0] * len(title))
        self.lines.append('')

    def add_section(self, name, depth=0):
        """Add a section.
        :type name: str
        :type depth: int
        """
        self.lines.append(name)
        self.lines.append(self.section_underlines[depth] * len(name))
        self.lines.append('')

    def add_raw_rst(self, content):
        """Add a raw RST.
        :type content: str
        """
        self.lines.append(content)

    def generate(self):
        """Generate RST content.
        :rtype: str
        """
        return '\n'.join(self.lines)
