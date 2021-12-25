# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functions to help with hashing."""

import hashlib

import aiofiles

from .. import app_context


async def verify_hash(filename: str, hash_digest: str, algorithm: str = 'sha256') -> bool:
    """
    Verify whether a file has a given sha256sum.

    :arg filename: The file to verify the sha256sum of.
    :arg hash_digest: The hash that is expected.
    :kwarg algorithm: The hash algorithm to use.  This must be present in hashlib on this
        system.  The default is 'sha256'
    :returns: True if the hash matches, otherwise False.
    """
    hasher = getattr(hashlib, algorithm)()
    async with aiofiles.open(filename, 'rb') as f:
        ctx = app_context.lib_ctx.get()
        # TODO: PY3.8: while chunk := await f.read(ctx.chunksize):
        chunk = await f.read(ctx.chunksize)
        while chunk:
            hasher.update(chunk)
            chunk = await f.read(ctx.chunksize)
    if hasher.hexdigest() != hash_digest:
        return False

    return True
