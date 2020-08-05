# Author: Felix Fontein <felix@fontein.de>
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""General functions for working with aiohttp."""

import pkgutil


def get_pkg_data(filename: str, package: str = 'antsibull.data') -> bytes:
    data = pkgutil.get_data(package, filename)
    if data is None:
        raise RuntimeError(f"Cannot find {filename} in the {package} package")
    return data
