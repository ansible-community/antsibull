# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""
Bootstrap logging for the antsibull commands.

Logging Setup
=============

An antsibull command should import the log from this module.  The module will setup an initial
logging configuration until the system can be initialized from configuration or other user defined
sources.  By default, the logging subsystem will log at the WARNING level or higher.  If the
:envvar:`ANTIBULL_EARLY_DEBUG` environment variable is set, then it will log at the debug level.

twiggy will emit these logs out to stderr until the command line application finishes the logging
configuration.  It should do this by getting the user specified logging configuration and then
calling :twiggy:`twiggy.dict_config` with that configuration to finish the setup.  This will look
something like this:

.. code-block:: python

    # File is antsibull/cli/antsibull_command.py
    import twiggy
    from ..app_logging import log
    from ..config import load_config

    mlog = log.fields(mod=__name__)

    def run(args):
        flog = mlog.fields(func='run')
        args = parse_args(args[0], args[1:])
        cfg = load_config(args.config_file)

        # Note: To be sure to get defaults, this may be better to tie into the app_ctx instead.
        if cfg.logging_cfg:
            twiggy.dict_config(cfg.logging_cfg.dict())

Once those steps are taken, any further logging calls will obey the user's configuration.

Usage within a module
=====================

Our convention for logging with twiggy is that the name field reflects the Python package that the
code is coming from (in this case, it is already set to ``antsibull`` by :mod:`antsibull.logging`.)
At the toplevel of a module, set up a logger which has a field named mod which reflects the module
name:

.. code-block:: python

    # The antsibull log object with name already set to `antsibull`.
    from logging import log

    # The logger you setup in each module.  This way the logs will be displayed with a field named
    # `mod` and the value set to the module name.
    mlog = log.fields(mod=__name__)

Inside of a function, you should further refine this by adding the name of the function in the
``func`` field.  If the function is a method of an object, include the class name so that you can
track down the proper function if there are multiple classes with the same method names:

.. code-block:: python

def test_function(argument1):
    flog = mlog.fields(func='test_function')
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

For information on which level you should log a message at, or more general information about
logging, see the :mod:`antsibull.logging` module documentation.
"""

import os

import twiggy
import twiggy.levels

# We want to see logs from the antsibull library, so the very first thing we do is
# turn the log level up to DEBUG.  That way individual emitters will be able to control the log
# level.
from .logging import log
log.min_level = twiggy.levels.DEBUG


# Temporarily setup logging with defaults until we can get real configuration.
_level = twiggy.levels.WARNING
if os.environ.get('ANTSIBULL_EARLY_DEBUG', False):
    _level = twiggy.levels.DEBUG
twiggy.quick_setup(min_level=_level)
