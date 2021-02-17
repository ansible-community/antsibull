# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""
Setup logging of the antsibull library.

By default, logging is disabled.  An application that wishes to use the log should import the log
from here before any other parts of antsibull are imported.  Then set `log.min_level` to the level
you want to log at.  For example:

.. code-block:: python

    import twiggy
    import twiggy.levels

    from antsibull.logging import log as antsibull_log

    antsibull_log.min_level = twiggy.levels.WARNING

The application will also want to setup some emitters to record or display the logs somewhere.
If you want logging but don't want to mess with it too deeply, you can use
:twiggy:func:`twiggy.quick_setup` to quickly configure that.

.. seealso::

    * :mod:`antsibull.app_logging` to see how the antsibull scripts bootstrap logging before
        running.
    * :mod:`antsibull.config` to see how the antsibull scripts allow user defined configuration
        to configure logging after the bootstrap phase is over.

.. note:: Logging levels

    Twiggy comes with several logging levels.  This is what they are and how the library uses
    them.  It can help you choose which log level is appropriate for you to use in your
    application by default.

    :CRITICAL: An error occurred that needs immediate attention.  The system cannot or should not
        continue if something critical happened.  Example: Unable to write output due to filesystem
        permissions.
    :ERROR: An error occurred that could be fixed in the future.  For instance, if the purpose is
        to parse multiple csv files and enter them into a database and we find that a single file
        won't parse as csv, this may be recorded as an error if the system processes the other csv
        files and enters them.
    :WARNING: Something happened that was unexpected to the program but the user has a choice
        whether to address or not.  For instance, if the program fails to find a config file
        in an expected location but it will operate from hardcoded defaults in that case, this
        would be a warning.
    :NOTICE: Something significant happened that would be important information for an end user.
        For instance, in a data processing pipeline, this could be used to record when each major
        step of the pipeline finished.
    :INFO: Something happened which could be interesting when a user of the system is trying to
        figure out why or what their commands are doing.  For example, a user may wonder why
        they are getting a file not found error on a config file they specified at the command
        line.  Knowing the filepath that the system is using when it tries to open the path
        will help them know that.
    :DEBUG: These are helpful for a programmer developing the code.  For example, information
        on functions being called (to trace through the execution path) would be appropriate here.
        Also relevant would be recording internal state of important variables or (occassionally)
        dumping data being operated upon.
"""
import twiggy

#: The standard log to use everywhere.  The name of the logger for all of the antsibull libraries
#: is antsibull so that it is easy to setup an emitter for all of antsibull.  For those used to
#: using the module's __name__ field as the name, the idiom we use here is to set the module name
#: in the ``mod`` field.
log = twiggy.log.name('antsibull').trace()  # pyre-ignore[16]: twiggy generates log dynamically
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


__all__ = ('log', 'plugin_filter')
