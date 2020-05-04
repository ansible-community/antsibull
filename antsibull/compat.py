# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Compat for older versions of Python."""

import asyncio
import sys


def _dummy():
    pass


if sys.version_info < (3, 7):
    #: In Python3.7+, :python:meth:`asyncio.get_running_loop` is the preferred way to get the loop.
    #: It gets the loop currently running.  When that's not available, we can use
    #: :meth:`asyncio.get_event_loop` which gets the default loop.  These are close to the same in
    #: our code since we use the default loop.  Just remember not to run it outside of an event
    #: loop.
    best_get_loop = asyncio.get_event_loop
    _loop = asyncio.get_event_loop()
    #: In Python3.7+, :python:meth:`asyncio.run` is the preferred way to enter an asyncio event loop
    #: and start to execute asynchronous code.  In earlier Pythons,
    #: :python:meth:`run_until_complete` can be used in almost the same manner since we are using
    #: the default event loop.
    asyncio_run = _loop.run_until_complete
else:
    best_get_loop = asyncio.get_running_loop
    asyncio_run = asyncio.run


__all__ = ('asyncio_run', 'best_get_loop')
