# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Toshio Kuratomi, 2021
"""Pydantic validators."""

import os.path


def convert_none(value):
    """
    Convert strings to Python None.

    When a setting is set to None in a config file, it could be the string "None" or "Null".
    This validator will convert those strings to  python None.
    """
    if isinstance(value, str) and value.lower() in ('none', 'null'):
        value = None
    return value


def _is_truthy_int(value):
    if value == 0:
        return False
    return True


def convert_bool(value):
    """
    Convert strings to Python True/False.

    True and False values may be specified in config files and the command line as strings.  This
    validator will convert a set of predetermined strings to Python True and False.
    """
    if isinstance(value, str):
        if value.lower() in ('false', 'no', 'n', 'f', ''):
            value = False
        elif value.lower() in ('true', 'yes', 'y', 't'):
            value = True
        else:
            try:
                value = int(value)
            # Any failure to convert to int just means the string does not map to a number.  We can
            # safely ignore that.
            except Exception:  # pylint: disable=broad-except
                pass
            else:
                value = _is_truthy_int(value)

    elif isinstance(value, int):
        value = _is_truthy_int(value)

    return value


def convert_path(value):
    """
    Expand `~` and environment variables in strings. Also convert strings like `None` and `Null`
    to None.
    """
    value = convert_none(value)

    if isinstance(value, str):
        value = os.path.expandvars(os.path.expanduser(value))

    return value
