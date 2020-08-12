# Author: Felix Fontein <felix@fontein.de>
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Helper to use pkgutil.get_data without having to check the return value."""

import pkgutil


def get_antsibull_data(filename: str) -> bytes:
    '''
    Retrieve data from the antsibull.data package as bytes.

    The filename can be a relative path separated with '/' to access subdirectories.
    See https://docs.python.org/3/library/pkgutil.html#pkgutil.get_data for details.
    '''
    data = pkgutil.get_data('antsibull.data', filename)
    if data is None:
        raise RuntimeError(f"Cannot find {filename} in the antsibull.data package")
    return data
