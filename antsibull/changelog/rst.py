# -*- coding: utf-8 -*-
# Author: Matt Clay <matt@mystile.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
ReStructuredText helpers.
"""

from typing import List


class RstBuilder:
    """
    Simple reStructuredText (RST) builder.
    """

    def __init__(self):
        """
        Create RST builder.
        """
        self.lines: List[str] = []
        self.section_underlines = '''=-~^.*+:`'"_#'''

    def set_title(self, title: str) -> None:
        """
        Add a document title. Must be called before other functions.

        :arg title: The document title
        """
        self.lines.append(self.section_underlines[0] * len(title))
        self.lines.append(title)
        self.lines.append(self.section_underlines[0] * len(title))
        self.lines.append('')

    def add_section(self, name: str, depth: int = 0) -> None:
        """
        Add a section.

        :arg name: The section title
        :arg depth: The section depth
        """
        self.lines.append(name)
        self.lines.append(self.section_underlines[depth] * len(name))
        self.lines.append('')

    def add_raw_rst(self, content: str) -> None:
        """
        Add a raw RST line.
        """
        self.lines.append(content)

    def generate(self) -> str:
        """
        Generate RST content.
        """
        return '\n'.join(self.lines)
