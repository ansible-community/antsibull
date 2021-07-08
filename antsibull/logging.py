# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""
The antsibull logging framework.

Logging should behave differently in a library versus an application setting.  As a library, the
logging messages should largely avoid assuming that the log has been configured sanely to display
messages.  That way a developer is not forced to understand and configure the log to start playing
with the library.

Once the library is used in an application, however, the application should give the user the
ability to configure the log.  At that point, the log should obey the user's choices.  We achieve
both of those goals by configuring the log for library output when the log is imported and then
initializing it for application usage when a set of functions are called.

.. seealso::

    * :mod:`antsibull.config` to see how the antsibull scripts allow user defined configuration
        to configure logging after the bootstrap phase is over.  This is the primary way that end
        users interact with the logging subsystem.


======================================
Logging from the library point of view
======================================

Merely importing this file sets up logging to be used as a library.  Essentially, this means that
logging output is disabled.  That way the library doesn't spam the user's screen with log messages.

An application that wishes to use the log must import the log and then call
antsibull.logging.initialize_app_logging() before any other parts of antsibull are imported.  See
the :ref:`Application Logging <application_logging>`_ section for more details.


Usage within a module
=====================

Our convention for logging with twiggy is that the name field reflects the Python package that the
code is coming from (in this case, it is already set to ``antsibull`` by :mod:`antsibull.logging`.)
At the toplevel of a module, set up a logger which has a field named ``mod`` which reflects the
module name:

.. code-block:: python

    # The antsibull log object with the name already set to `antsibull`.
    from logging import log

    # mlog stands for module log.  It's our convention to create a logger from the
    # antsibull.logging.log object in each module.  `fields()` takes an arbitrary set of keyword
    # args and returns a new log object.  Any log messages we emit with this log object (or its
    # children) will include the fields which were set on it.  Our convention is to create mlog with
    # `fields(mod=__name__)` so that messages we make from mlog (or its children) have a field named
    # `mod` containing the name of the module.

    # `mod` and the value set to the module name.
    mlog = log.fields(mod=__name__)

    TRICKY_COMPUTED_GLOBAL = [a**a for a in range(1, 4)]
    # Use mlog for logging interesting things that happen at the module level.  Notice that we send
    # the value of TRICKY_COMPUTED_GLOBAL in fields() rather than in debug().  Most twiggy emitters
    # format fields so that they're machine parsable whereas the message is freeform text.  Using
    # fields for things that make sense to be viewed as key=value allows for human readable but
    # machine parsable structured output.  For instance, this is the default output format:
    # DEBUG:antsibull:computed_global=[1, 4, 27]:mod=__main__|globals computed at module level
    mlog.fields(computed_global=TRICKY_COMPUTED_GLOBAL).debug('globals computed at module level')

Inside of a function, you should further refine this by creating a new log object with the name of
the function in the ``func`` field.  If the function is a method of an object, include the class
name so that you can track down the proper function if there are multiple classes with the same
method names:

.. code-block:: python

def test_function(argument1):
    # flog stands for function log.  It's our convention to use this name.
    # Create a new one in any function you want to log from.
    # By creating this from mlog, we copy any fields and other settings that we made to mlog.
    # Our convention is to use the `func` field to hold the name of the function we're in.
    flog = mlog.fields(func='test_function')

    # This would output:
    # DEBUG:antsibull:func=test_function:mod=__main__|Enter
    flog.debug('Enter')
    value = do_something(argument1)

    flog.debug('Leave')

class FooBar:
    def __init__(self):
        flog = mlog.fields(func='FooBar.__init__')
        flog.debug('Enter')

        self._x = initialize_x()
        self._y = initialize_y()

        self.position = self.calculate_position(self._x, self._y)

        flog.debug('Leave')


.. _logging_levels::

Logging levels
==============

Twiggy comes with several logging levels.  This is what they are and how the antsibull library uses
them.  It can help you choose which log level is appropriate to use in your application by default.

:CRITICAL: An error occurred that needs immediate user attention.  The system cannot or should not
    continue if something critical happened.  Example: Unable to write output due to filesystem
    permissions.
:ERROR: An error occurred that could be fixed by the user in the future.  For instance, if the
    purpose is to parse multiple csv files and enter them into a database and we find that a single
    file won't parse as csv, this may be recorded as an error if the system processes the other csv
    files and enters them.
:WARNING: Something happened that was unexpected to the program but the user has a choice
    whether to address or not.  For instance, if the program fails to find a config file
    in an expected system location but it will operate from hardcoded defaults in that case, this
    would be a warning.
:NOTICE: Something significant happened that would be important information for an end user.
    For instance, in a data processing pipeline, this could be used to record when each **major**
    step of the pipeline finished.
:INFO: Something happened which could be interesting when a user of the system is trying to
    figure out why or what their commands are doing.  For example, a user may wonder why
    they are getting a file not found error on a config file they specified at the command
    line.  Knowing the filepath that the system is using when it tries to open the path
    will help them know that.
:DEBUG: This is similar to ``INFO`` but only helpful for a programmer developing the code.  For
    example, information on functions being called (to trace through the execution path) would be
    appropriate here.  Also relevant would be recording internal state of important variables or
    (occassionally) dumping data being operated upon.


.. _application_logging::

==========================================
Logging from the application point of view
==========================================


Logging Setup
=============

An antsibull command (:file:`antsibull/cli/*.py`) should import the ``log`` object from this module.
The log object will be configured for use within the library at first (silent) so the application
should call :func:`antsibull.logging.initialize_app_logging` as soon as possible to tell the ``log``
that it is okay to emit messages.

The initial application logging configuration will log to stderr at the ``WARNING`` level or
higher.  If the :envvar:`ANTIBULL_EARLY_DEBUG` environment variable is set, then  it will log at
the ``DEBUG`` level rather than ``WARNING``.

The antsibull command should read the configuration settings, which may include user specified
logging configuration and application defaults, and then call :twiggy:func:`twiggy.dict_config` to
finish the setup.  At that point, logging calls will emit logs according to the user's
configuration.

Here's a sample of the relevant portions of an antsibull command to show how this will look:

.. code-block:: python

    # File is antsibull/cli/antsibull_command.py
    import twiggy
    # log is the toplevel log object.  It is important to import this and initialize it prior to
    # using the log so that sane defaults can be set.
    from ..logging import log, initialize_app_logging

    # By default, the log is configured to be useful within a library where the user may not have
    # been given the chance to configure the log.  Calling initialize_app_logging() reconfigures
    # the log to a more verbose state which the user can then configure.  This must be done before
    # any antsibull modules which setup their own loggers ( mlog = log.fields(__name__)) happen as
    # each of those loggers will copy the settings that log has at the time they are created.
    initialize_app_logging()

    from ..config import load_config


    mlog = log.fields(mod=__name__)

    def run(args):
        flog = mlog.fields(func='run')
        args = parse_args(args[0], args[1:])
        cfg = load_config(args.config_file)

        context_data = app_context.create_contexts(args=args, cfg=cfg)
        with app_context.app_and_lib_context(context_data) as (app_ctx, dummy_):
            # initialize_app_logging() sets the log's configuration with defaults appropriate for
            # an application but this call takes that one step further. It takes the logging
            # configuration from the user's config file and hands it to twiggy.dict_config() so
            # that the user has ultimate control over what log level, what format, and which file
            # the log is output as.  See the twiggy documentation for information on the format of
            # the logging config.  See the antsibull.app_context documentation if you want more
            # information on the context object.
            twiggy.dict_config(app_ctx.logging_cfg.dict())


Once those steps are taken, any further logging calls will obey the user's configuration.

"""
import os

import twiggy
import twiggy.levels

#: The standard log to use everywhere.  The name of the logger for all of the antsibull libraries
#: is antsibull so that it is easy to setup an emitter for all of antsibull.  For those used to
#: using the module's __name__ field as the name, the idiom we use here is to set the module name
#: in the ``mod`` field.
log = twiggy.log.name('antsibull').trace()  # pyre-ignore[16]: twiggy generates log dynamically

# We disable logging at the library level so that we don't unnecessarily spam the user with output.
# Applications which use the library should re-enable this and give the user the ability to control
# what output gets logged.  See the antisbull.logging docstring for more information.
log.min_level = twiggy.levels.DISABLED

mlog = log.fields(mod=__name__)
mlog.debug('logging loaded')


def plugin_filter():
    """
    Filter out messages which come from plugin error output.

    :arg msg: A :twiggy:obj:`twiggy.message.Message` object which would be filtered
    """
    def wrapped(msg):
        return (
            msg.fields['func'] == 'write_plugin_rst' and
            msg.fields['mod'] == 'antsibull.write_docs'
        )
    return wrapped


def initialize_app_logging():
    """
    Change log settings to make sense for an application.

    Merely importing the :mod:`antsibull.logging` module sets up the logger for use as part of
    a library.  Calling this function will initialize the logger for use in an application.
    """
    # We want to see logs from the antsibull library, so the very first thing we do is turn the log
    # level up to DEBUG.  That way individual emitters will be able to control the log level.
    log.min_level = twiggy.levels.DEBUG

    # Temporarily setup logging with defaults until we can get configuration from the user.
    _level = twiggy.levels.WARNING
    if os.environ.get('ANTSIBULL_EARLY_DEBUG', False):
        _level = twiggy.levels.DEBUG
    twiggy.quick_setup(min_level=_level)


__all__ = ('log', 'initialize_app_logging', 'plugin_filter')
