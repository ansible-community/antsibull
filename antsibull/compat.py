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
    #: In Python3.7+, :python:func:`asyncio.get_running_loop` is the preferred way to get the loop.
    #: It gets the loop currently running.  When that's not available, we can use
    #: :python:func:`asyncio.get_event_loop` which gets the default loop.  These are close to the
    #: same in our code since we use the default loop.  Just remember not to run it outside of an
    #: event loop.
    best_get_loop = asyncio.get_event_loop

    _loop = asyncio.get_event_loop()
    #: In Python3.7+, :python:func:`asyncio.run` is the preferred way to enter an asyncio event loop
    #: and start to execute asynchronous code.  In earlier Pythons,
    #: :python:func:`run_until_complete` can be used in almost the same manner since we are using
    #: the default event loop.
    asyncio_run = _loop.run_until_complete

    #: In Python3.7+, :python:func:`asyncio.create_task` is the preferred way to schedule additional
    #: coroutines for execution.  In earlier Pythons, :python:func:`asyncio.ensure_future` can be
    #: used, it's just not as readable.
    create_task = asyncio.ensure_future
else:
    best_get_loop = asyncio.get_running_loop
    asyncio_run = asyncio.run
    create_task = asyncio.create_task

if sys.version_info < (3, 8):
    #: In Python3.8+, :python:module:`importlib.metadata` exists to get information about installed
    #: python packages.  In earlier versions of Python, we can use the importlib_metadata backport
    #: from pypi.
    import importlib_metadata as metadata
else:
    from importlib import metadata

if sys.version_info < (3, 9):
    #: In Python3.9+, argparse.BooleanOptionalAction gives us a simple way to add
    #: --feature/--no-feature command line switches.  In earluer versions, we use
    #: code that we've copied from the upstream code.
    from .vendored._argparse_booleanoptionalaction import BooleanOptionalAction
else:
    from argparse import BooleanOptionalAction

__all__ = ('BooleanOptionalAction', 'asyncio_run', 'best_get_loop', 'create_task', 'metadata')
