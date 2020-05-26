# -*- coding: utf-8 -*-
# Author: Matt Clay <matt@mystile.com>
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Utility functions.
"""

import re

import semantic_version

from .config import ChangelogConfig


def is_release_version(config: ChangelogConfig, version: str) -> bool:
    """
    Determine the type of release from the given version.

    :arg config: The changelog configuration
    :arg version: The version to check
    :return: Whether the provided version is a release version
    """
    if config.is_collection:
        return not bool(semantic_version.Version(version).prerelease)

    tag_format = 'v%s' % version

    if re.search(config.pre_release_tag_re, tag_format):
        return False

    if re.search(config.release_tag_re, tag_format):
        return True

    raise Exception('unsupported version format: %s' % version)
