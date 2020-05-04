# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functions to handle config files."""


import perky

from .logging import log
from .schemas.config import ConfigSchema


mlog = log.fields(mod=__name__)


def load_config(filename: str) -> ConfigSchema:
    """
    Parse a config file and return the data from it.

    :arg filename: The filename of the config file to parse.
    :returns: A ConfigSchema model containing the data.
    """
    raw_config_data = perky.load(filename)
    config_data = ConfigSchema.parse_obj(raw_config_data)
    return config_data
