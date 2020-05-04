# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functions to setup logging."""
import twiggy

# Temporarily setup twiggy logging with defaults until we can get real configuration.
twiggy.quick_setup()

#: The standard log to use everywhere.  The name of the logger reflects the project that
#: the logger is used within.  For those used to using the module's __name__ field as the name, the
#: idiom we use here is to set the module name in the `mod` field.
log = twiggy.log.name('antsibull')
log.min_level = twiggy.levels.DISABLED

# This is how to setup the logger to use in your module
mlog = log.fields(mod=__name__)
mlog.debug('logging loaded')

__all__ = ('log',)
