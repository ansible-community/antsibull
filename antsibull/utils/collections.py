# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""General functions for working with python collections and classes for new data types."""

import typing as t
from collections.abc import Sequence, Set


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


def compare_all_but(dict_a: t.Mapping, dict_b: t.Mapping,
                    keys_to_ignore: t.Optional[t.Iterable] = None) -> bool:
    """
    Compare two dictionaries, with the possibility to ignore some fields.

    :arg dict_a: First dictionary to compare
    :arg dict_b: Second dictionary to compare
    :kwarg keys_to_ignore: An iterable of keys whose values in the dictionaries will not be
        compared.
    :returns: True if the dictionaries have matching values for all of the keys which were not
        ignored.  False otherwise.
    """
    if keys_to_ignore is None:
        return dict_a == dict_b

    if not isinstance(keys_to_ignore, Set):
        keys_to_ignore = frozenset(keys_to_ignore)

    length_a = len(frozenset(dict_a.keys()) - keys_to_ignore)
    length_b = len(frozenset(dict_b.keys()) - keys_to_ignore)

    if length_a != length_b:
        return False

    sentinel = object()

    for key, value in ((k, v) for k, v in dict_a.items() if k not in keys_to_ignore):
        if value != dict_b.get(key, sentinel):
            return False

    return True
