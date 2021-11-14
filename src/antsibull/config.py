# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functions to handle config files."""

import itertools
import os.path
import typing as t

import perky

from .logging import log
from .schemas.config import ConfigModel


mlog = log.fields(mod=__name__)

#: System config file location.
SYSTEM_CONFIG_FILE = '/etc/antsibull.cfg'

#: Per-user config file location.
USER_CONFIG_FILE = '~/.antsibull.cfg'


def find_config_files(conf_files: t.Iterable[str]) -> t.List[str]:
    """
    Find all config files that exist.

    :arg conf_files: An iterable of config filenames to search for.
    :returns: A List of filenames which actually existed on the system.
    """
    flog = mlog.fields(func='find_config_file')
    flog.fields(conf_files=conf_files).debug('Enter')

    paths = [os.path.abspath(p) for p in conf_files]
    flog.fields(paths=paths).info('Paths to check')

    config_files = []
    for conf_path in paths:
        if os.path.exists(conf_path):
            config_files.append(conf_path)
    flog.fields(paths=config_files).info('Paths found')

    flog.debug('Leave')
    return config_files


def read_config(filename: str) -> ConfigModel:
    """
    Parse a config file and return the data from it.

    :arg filename: The filename of the config file to parse.
    :returns: A ConfigModel model containing the config data.
    """
    flog = mlog.fields(func='read_config')
    flog.debug('Enter')

    filename = os.path.abspath(filename)

    flog.fields(filename=filename).info('loading config file')
    raw_config_data = perky.load(filename)
    flog.debug('Validatinging the config file data')
    # Note: We parse the object but discard the model because we want to validate the config but let
    # the context handle all setting of defaults
    ConfigModel.parse_obj(raw_config_data)

    flog.debug('Leave')
    return raw_config_data


def load_config(conf_files: t.Union[t.Iterable[str], str, None] = None) -> t.Dict:
    """
    Load configuration.

    Load configuration from all found conf files.  The default configuration is loaded
    followed by a system-wide location, user-location, and then any files specified in
    the ``conf_files`` parameter.  Toplevel keys in later files will overwrite earlier
    those same keys in earlier files.

    :arg conf_files: An iterable of conf_files to load configuration information from.
    :returns: A dict containing the configuration.
    """
    flog = mlog.fields(func='load_config')
    flog.debug('Enter')

    if isinstance(conf_files, str):
        conf_files = (conf_files,)
    elif conf_files is None:
        conf_files = ()

    user_config_file = os.path.expanduser(USER_CONFIG_FILE)
    available_files = find_config_files(itertools.chain((SYSTEM_CONFIG_FILE, user_config_file),
                                                        conf_files))

    includes = list(available_files)

    flog.debug('loading config files')
    # Perky has some bugs that prevent this simple way from working:
    # https://github.com/ansible-community/antsibull/pull/118
    # cfg = {'includes': includes}
    # cfg = perky.includes(cfg, recursive=True)

    # Workaround for above bug.  Note that includes specified in the config files will not work
    # but we can just add that as a new feature when perky gets it working.
    cfg = {}
    for filename in includes:
        new_cfg = perky.load(filename)
        cfg.update(new_cfg)

    flog.debug('validating configuration')
    # Note: We parse the object but discard the model because we want to validate the config but let
    # the context handle all setting of defaults
    ConfigModel.parse_obj(cfg)

    flog.fields(config=cfg).debug('Leave')
    return cfg
