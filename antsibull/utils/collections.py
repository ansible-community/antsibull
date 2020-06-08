# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""General functions for working with collections and classes for new data types."""

import typing as t
from collections.abc import Sequence


def is_sequence(obj: t.Any, include_string: bool = False) -> bool:
    """
    Return whether ``obj`` is a :python:obj:`collections.abc.Sequence`.

    You often want to know if a variable refers to a Sequence container but treat strings as being
    scalars instead of being Sequences.  This function allows you to do that.

    :arg obj: The object to test to see if it is a Sequence.
    :kwarg include_string: When False, strings are treated as not being a Sequence.  When True,
        they are.
    :returns: True if the object is a :python:obj:`collections.abc.Sequence`, False if it is not.
        Excludes strings from being a type of Sequence if ``include_string`` is False.
    """
    if isinstance(obj, (str, bytes)) and not include_string:
        return False
    if isinstance(obj, Sequence):
        return True
    return False
