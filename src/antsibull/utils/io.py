# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2021
"""I/O helper functions."""

import os
import os.path

import aiofiles

from .. import app_context
from ..logging import log


mlog = log.fields(mod=__name__)


async def copy_file(source_path: str, dest_path: str) -> None:
    """
    Copy content from one file to another.

    :arg source_path: Source path. Must be a file.
    :arg dest_path: Destination path.
    """
    flog = mlog.fields(func='copy_file')
    flog.debug('Enter')

    lib_ctx = app_context.lib_ctx.get()
    if lib_ctx.file_check_content > 0:
        # Check whether the destination file exists and has the same content as the source file,
        # in which case we won't overwrite the destination file
        try:
            stat_d = os.stat(dest_path)
            if stat_d.st_size <= lib_ctx.file_check_content:
                stat_s = os.stat(source_path)
                if stat_d.st_size == stat_s.st_size:
                    # Read both files and compare
                    async with aiofiles.open(source_path, 'rb') as f_in:
                        content_to_copy = await f_in.read()
                    async with aiofiles.open(dest_path, 'rb') as f_in:
                        existing_content = await f_in.read()
                    if content_to_copy == existing_content:
                        flog.debug('Skipping copy, since files are identical')
                        return
                    # Since we already read the contents of the file to copy, simply write it to
                    # the destination instead of reading it again
                    async with aiofiles.open(dest_path, 'wb') as f_out:
                        f_out.write(content_to_copy)
                    return
        except FileNotFoundError:
            # Destination (or source) file does not exist
            pass

    async with aiofiles.open(source_path, 'rb') as f_in:
        async with aiofiles.open(dest_path, 'wb') as f_out:
            # TODO: PY3.8: while chunk := await f.read(lib_ctx.chunksize)
            chunk = await f_in.read(lib_ctx.chunksize)
            while chunk:
                await f_out.write(chunk)
                chunk = await f_in.read(lib_ctx.chunksize)

    flog.debug('Leave')


async def write_file(filename: str, content: str) -> None:
    flog = mlog.fields(func='write_file')
    flog.debug('Enter')

    content_bytes = content.encode('utf-8')

    lib_ctx = app_context.lib_ctx.get()
    if lib_ctx.file_check_content > 0 and len(content_bytes) <= lib_ctx.file_check_content:
        # Check whether the destination file exists and has the same content as the one we want to
        # write, in which case we won't overwrite the file
        try:
            stat = os.stat(filename)
            if stat.st_size == len(content_bytes):
                # Read file and compare
                async with aiofiles.open(filename, 'rb') as f:
                    existing_content = await f.read()
                if existing_content == content_bytes:
                    flog.debug('Skipping write, since file already contains the exact content')
                    return
        except FileNotFoundError:
            # Destination file does not exist
            pass

    async with aiofiles.open(filename, 'wb') as f:
        await f.write(content_bytes)

    flog.debug('Leave')


async def read_file(filename: str, encoding: str = 'utf-8') -> str:
    flog = mlog.fields(func='read_file')
    flog.debug('Enter')

    async with aiofiles.open(filename, 'r', encoding=encoding) as f:
        content = await f.read()

    flog.debug('Leave')
    return content
