# -*- coding: utf-8 -*-
# Author: Matt Clay <matt@mystile.com>
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Utility functions.
"""

import logging
import re

import semantic_version
import yaml


LOGGER = logging.getLogger('changelog')


def load_galaxy_metadata(paths):
    """Load galaxy.yml metadata.
    :type paths: PathsConfig
    :rtype: dict
    """
    with open(paths.galaxy_path, 'r') as galaxy_fd:
        return yaml.safe_load(galaxy_fd)


def is_release_version(config, version):
    """Deterine the type of release from the given version.
    :type config: ChangelogConfig
    :type version: str
    :rtype: bool
    """
    if config.is_collection:
        return not bool(semantic_version.Version(version).prerelease)

    tag_format = 'v%s' % version

    if re.search(config.pre_release_tag_re, tag_format):
        return False

    if re.search(config.release_tag_re, tag_format):
        return True

    raise Exception('unsupported version format: %s' % version)
