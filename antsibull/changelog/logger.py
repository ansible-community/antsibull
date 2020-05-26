# -*- coding: utf-8 -*-
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Provide global logger.
"""

import logging
import sys


class FormattingAdapter(logging.LoggerAdapter):
    """
    By default, the logging framework does not allow to format messages
    other than by % formatting, except by jumping through loops. This
    makes {} formatting work with the least amount of work.

    The idea is similar to the one in https://stackoverflow.com/a/24683360
    """

    def __init__(self, logger):
        super().__init__(logger, {})
        self.logger_args = ['exc_info', 'extra', 'stack_info']

    def log(self, level, msg, *args, **kwargs):
        """
        Forward log calls with formatted message.
        """
        if self.isEnabledFor(level):
            log_kwargs = {
                key: kwargs[key] for key in self.logger_args if key in kwargs
            }
            self.logger._log(  # pylint: disable=protected-access
                level, msg.format(*args, **kwargs), (), **log_kwargs)

    def addHandler(self, *args, **kwargs):  # pylint: disable=invalid-name
        """
        Forward addHandler call.
        """
        self.logger.addHandler(*args, **kwargs)


LOGGER = FormattingAdapter(logging.getLogger('changelog'))


def setup_logger(verbosity: int) -> None:
    """
    Setup logger.
    """
    formatter = logging.Formatter('%(levelname)s %(message)s')

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.WARN)

    if verbosity > 2:
        LOGGER.setLevel(logging.DEBUG)
    elif verbosity > 1:
        LOGGER.setLevel(logging.INFO)
    elif verbosity > 0:
        LOGGER.setLevel(logging.WARN)
