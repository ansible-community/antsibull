# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Toshio Kuratomi, 2019
"""
Setup an application context to save global data which is set on program start.

There is some application data which is set on application startup and then never modified.
These values are *almost* constants and should be eligible to be global variables.  However,
global variables make testing hard (as the test has to monkeypatch constants) and the use of
globals prevents re-using the functionality as a library.

Enter contexts.  Contexts can be used to set global values.  But the context can be swapped out if
the program needs to use a different set of globals and some location for some reason.  This file
contains the context framework itself.

For Python3.6 compatibility, this file needs to be loaded early, before any event loops are created.
This is due to limitations in the backport of the contextvars library to Python3.6.  For code which
targets Python3.7 and above, there is no such limitation.

.. warning:: This is not a stable interface.

    The API has quite a few rough edges that need to be ironed out before this is finished.  Some of
    this code and data will be moved into an antibull.context module which can deal with the generic
    side of things while this module will only contain the things that are particular to specfic
    applications.

Setup
=====

Importing antsibull.app_context will setup a default context with default values for the library to
use.  The application should initialize a new context with user overriding values by calling
:func:`antsibull.app_context.create_contexts` with command line args and configuration data.  The
data from those will be used to initialize a new app_ctx and new lib_ctx.  The application can then
use the context managers to utilize these contexts before calling any further antsibull code.  An
example:

.. code-block:: python

    def do_something():
        app_ctx = app_context.app_ctx.get()
        core_filename = download_python_package('ansible-core', server_url=app_ctx.pypi_url)
        return core_filename

    def run(args):
        args = parsre_args(args)
        cfg = load_config(args.config_file)
        context_data = app_context.create_contexts(args=args, cfg=cfg)
        with app_and_lib_context(context_data):
            do_something()
"""

import argparse
import contextvars
import functools
import sys
import typing as t
from contextlib import contextmanager

from .schemas.context import AppContext, LibContext
from .vendored.collections import ImmutableDict

if sys.version_info < (3, 7):
    # contextvars for Python3.6.  It uses a backport of contextvars which takes over the contextvars
    # import slot there and aiocontextvars which adds the needed asyncio support.
    import aiocontextvars  # noqa: F401, pylint:disable=unused-import


#: Field names in the args and config whose value will be added to the app_ctx
_FIELDS_IN_APP_CTX = frozenset(('ansible_base_url', 'breadcrumbs', 'galaxy_url', 'indexes',
                                'logging_cfg', 'pypi_url', 'use_html_blobs', 'collection_cache'))

#: Field names in the args and config whose value will be added to the lib_ctx
_FIELDS_IN_LIB_CTX = frozenset(
    ('chunksize', 'doc_parsing_backend', 'max_retries', 'process_max', 'thread_max'))

#: lib_ctx should be restricted to things which do not belong in the API but an application or
#: user might want to tweak.  Global, internal, incidental values are good to store here.  Things
#: that are already settable by the public API are not.  For instance, a function whose primary
#: purpose is to retrieve a file from the internet and return the filename where it was
#: downloaded to might need a number of bytes to read at a time so that the entire file contents
#: aren't in memory at one time.  The number of bytes is incidental and an internal
#: implementation detail.  However, it might be something that an end user wants to adjust
#: globally for all functions which need to chunk data.  So this is appropriate to make available
#: for tweaking via a value saved in lib_ctx.  All values in lib_ctx need to have a default value
#: so that code which uses it can fallback to something if the application or user did not
#: specify a value.
lib_ctx = contextvars.ContextVar('lib_ctx')

#: Values in app_ctx are things that form defaults in the application.  Even though it may be
#: tempting to use them for library API, they should not be used there.  Instead, these values
#: are things that should be pat of the API calls themselves and explicitly passed from the
#: application to the library code.  If the value is used by multiple calls to the function (or
#: by calls to multiple related functions) it may be convenient to encapsulate that library code
#: into an object which can be initialized with the data.
#:
#: For instance, a function might contact a web service to retrieve information.  The URL of the
#: web service can be passed in via the API for testing against a non-production server.  The
#: user might toggle these via a config file or command line argument.  The app_ctx provides
#: a place for the application to consolidate the information from these different locations into
#: a single place and then consult them globally.  The values should be passed explicitly from
#: the application code to the library code as a function parameter.
#:
#: If the library provides several functions to retrieve different pieces of information from the
#: server, the library can provide a class which takes the server's URL as a parameter and stores
#: as an attribute and the functions can be converted into methods of the object.  Then the
#: application code can initialize the object once and thereafter call the object's methods.
app_ctx = contextvars.ContextVar('app_ctx')


class ContextReturn(t.NamedTuple):
    """
    NamedTuple for the return value of :func:`create_contexts`.

    The :func:`create_contexts` returns quite a bit of information.  This data structure organizes
    the information.

    :ivar app_ctx: Context for vars that are okay to use globally only within application code.
    :ivar lib_ctx: Context for vars which may be used globally within both library and
        application code.
    :ivar args: An :python:obj:`argparse.Namespace` containing command line arguments that were not
        used to construct the contexts
    :ivar cfg: Configuration values which were not used to construct the contexts.
    """

    app_ctx: AppContext
    lib_ctx: LibContext
    args: argparse.Namespace
    cfg: t.Dict


def _extract_context_values(known_fields, args: t.Optional[argparse.Namespace],
                            cfg: t.Mapping = ImmutableDict()) -> t.Dict:

    context_values = {}
    if cfg:
        for value in known_fields:
            try:
                context_values[value] = cfg[value]
            except KeyError:
                pass

    # Args override config
    if args:
        for value in known_fields:
            try:
                context_values[value] = getattr(args, value)
            except AttributeError:
                pass

    return context_values


_extract_lib_context_values = functools.partial(_extract_context_values, _FIELDS_IN_LIB_CTX)
_extract_app_context_values = functools.partial(_extract_context_values, _FIELDS_IN_APP_CTX)


def create_contexts(args: t.Optional[argparse.Namespace] = None,
                    cfg: t.Mapping = ImmutableDict(),
                    use_extra: bool = True) -> ContextReturn:
    """
    Create new contexts appropriate for setting the app and lib context.

    This function takes values from the application arguments and configuration and sets them on
    the context.  It validates, normalizes, and sets defaults for the contexts based on what is
    available in the arguments and configuration.

    :kwarg args: An :python:obj:`argparse.Namespace` holding the program's command line
        arguments.  See the warning below about working with :python:mod:`argpase`.
    :kwarg cfg: A dictionary holding the program's configuration.
    :kwarg use_extra: When True, the default, all extra arguments and config values will be set as
        fields in ``app_ctx.extra``.  When False, the extra arguments and config values will be
        returned as part of the ContextReturn.
    :returns: A ContextReturn NamedTuple.

    .. warning::
        We cannot tell whether a user set a value via the command line if :python:mod:`argparse`
        sets the field to a default value.  That means when you specify the field in the
        :obj:`AppContext` or :obj:`LibContext` models, you must tell :python:mod:`argparse` not to
        set the field to a default like this::

            parser.add_argument('--breadcrumbs', default=argparse.SUPPRESS)

        If the field is only used via the :attr:`AppContext.extra` mechanism (not explictly set),
        then you should ignore this section and use :python:mod:`argparse`'s default mechanism.
    """
    lib_values = _extract_lib_context_values(args, cfg)
    app_values = _extract_app_context_values(args, cfg)

    #
    # Save the unused values
    #
    known_fields = _FIELDS_IN_APP_CTX.union(_FIELDS_IN_LIB_CTX)

    unused_cfg = {}
    if cfg:
        unused_cfg = {k: v for k, v in cfg.items() if k not in known_fields}

    unused_args = {}
    if args:
        unused_args = {k: v for k, v in vars(args).items() if k not in known_fields}

    # Unused values are saved in app_ctx.extra when use_extra is set
    if use_extra:
        unused_cfg.update(unused_args)
        app_values['extra'] = unused_cfg
        unused_cfg = {}
        unused_args = {}

    unused_args = argparse.Namespace(**unused_args)

    # create new app and lib ctxt from the application's arguments and config.
    local_app_ctx = AppContext(**app_values)
    local_lib_ctx = LibContext(**lib_values)

    return ContextReturn(
        app_ctx=local_app_ctx, lib_ctx=local_lib_ctx, args=unused_args, cfg=unused_cfg)


def _copy_lib_context():
    try:
        old_context = lib_ctx.get()
    except LookupError:
        old_context = LibContext()

    # Copy just in case contexts are allowed to be writable in the the future
    return old_context.copy()


def _copy_app_context():
    try:
        old_context = app_ctx.get()
    except LookupError:
        old_context = AppContext()

    # Copy just in case contexts are allowed to be writable in the the future
    return old_context.copy()


@contextmanager
def lib_context(new_context: t.Optional[LibContext] = None):
    """
    Set up a new lib_context.

    :kwarg new_context: New lib context to setup.  If this is None, the context is set to a copy of
        the old context.
    """
    if new_context is None:
        new_context = _copy_lib_context()

    reset_token = lib_ctx.set(new_context)
    yield new_context

    lib_ctx.reset(reset_token)


@contextmanager
def app_context(new_context: t.Optional[AppContext] = None):
    """
    Set up a new app_context.

    :kwarg new_context: New app context to setup.  If this is None, the context is set to a copy of
        the old context.
    """
    if new_context is None:
        new_context = _copy_app_context()

    reset_token = app_ctx.set(new_context)
    yield new_context

    app_ctx.reset(reset_token)


@contextmanager
def app_and_lib_context(context_data: ContextReturn):
    """
    Set the app and lib context at the same time.

    This is a convenience wrapper around the :func:`app_context` and :func:`lib_context`
    context managers.  It's meant to be used with :func:`create_contexts` like this:

    .. code_block:: python

        context_data = create_contexts(args=args, cfg=cfg)

        with app_and_lib_context(context_data):
            do_something()
    """
    with lib_context(context_data.lib_ctx) as new_lib_ctx:
        with app_context(context_data.app_ctx) as new_app_ctx:
            yield (new_app_ctx, new_lib_ctx)


#
# Set initial contexts with default values
#
lib_ctx.set(LibContext())
app_ctx.set(AppContext())
