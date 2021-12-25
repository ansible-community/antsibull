# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functions for working with tarballs."""
import re

import sh


#: Regex to find toplevel directories in tar output
TOPLEVEL_RE: re.Pattern = re.compile('^[^/]+/$')


class InvalidTarball(Exception):
    """Raised when a requested version does not exist."""


async def unpack_tarball(tarname: str, destdir: str) -> str:
    """
    Unpack a tarball.

    :arg tarname: The tarball to unpack.
    :arg destdir: The destination to unpack into.
    :returns: Toplevel of the unpacked directory structure.  This will be
        a subdirectory of `destdir`.
    """
    # FIXME: Need to run tar via run_in_executor()
    # FIXME: Use unpack_tarball for places that are manually calling tar now
    # pyre-ignore[16]
    manifest = sh.tar('-xzvf', tarname, f'-C{destdir}')  # pylint:disable=no-member
    toplevel_dirs = [filename for filename in manifest if TOPLEVEL_RE.match(filename)]

    if len(toplevel_dirs) != 1:
        raise InvalidTarball(f'The tarball {tarname} had more than a single toplevel dir')

    expected_dirname = tarname[:-len('.tar.gz')]
    if toplevel_dirs[0] != expected_dirname:
        raise InvalidTarball(f'The directory in {tarname} was not {expected_dirname}')

    return toplevel_dirs[0]


async def pack_tarball(tarname: str, directory: str) -> str:  # pylint:disable=unused-argument
    pass
