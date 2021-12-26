# -*- coding: utf-8 -*-
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2021

"""
YAML handling.
"""

import typing as t

import yaml

_SafeLoader: t.Any
_SafeDumper: t.Any
try:
    # use C version if possible for speedup
    from yaml import CSafeLoader as _SafeLoader
    from yaml import CSafeDumper as _SafeDumper
except ImportError:
    from yaml import SafeLoader as _SafeLoader
    from yaml import SafeDumper as _SafeDumper


def load_yaml_bytes(data: bytes) -> t.Any:
    """
    Load and parse YAML from given bytes.
    """
    return yaml.load(data, Loader=_SafeLoader)


def load_yaml_file(path: str) -> t.Any:
    """
    Load and parse YAML file ``path``.
    """
    with open(path, 'rb') as stream:
        return yaml.load(stream, Loader=_SafeLoader)


def store_yaml_file(path: str, content: t.Any) -> None:
    """
    Store ``content`` as YAML file under ``path``.
    """
    with open(path, 'wb') as stream:
        dumper = _SafeDumper
        dumper.ignore_aliases = lambda *args: True
        yaml.dump(content, stream, default_flow_style=False, encoding='utf-8', Dumper=dumper)
