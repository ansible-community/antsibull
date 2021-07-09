# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Augment data from plugin documenation with additional values."""

import typing as t


def add_full_key(options_data: t.Mapping[str, t.Any], suboption_entry: str,
                 _full_key: t.Optional[list] = None) -> None:
    """
    Add information on the strucfture of a dict value in options or returns.

    suboptions and contains are used for nested information (an option taking a dict which has
    a deeply nested structure, for instance.)  They describe each entry into the dict.  When
    constructing documentation which uses that, it can be useful to know the hierarchy leads to
    that entry (for instance, to make a target for an html href).  This function adds that
    information to a ``full_key`` field on the suboptions' entry.

    :arg options_data: The documentation data which is going to be analyzed and updated.
    :arg suboption_entry: The name of the suboptions key in the data.  For options data, this is
        ``suboptions``.  For returndocs, it is ``contains``.
    :kwarg _full_key: This is a recursive function.  After we pass the first level of nesting,
        ``_full_key`` is set to record the names of the upper levels of the hierarchy.

    .. warning:: This function operates by side-effect.  The options_data dictionay is modified
        directly.
    """
    if _full_key is None:
        _full_key = []

    for (key, entry) in options_data.items():
        # Make sure that "full key" is contained
        full_key_k = _full_key + [key]
        entry['full_key'] = full_key_k

        # Process suboptions
        suboptions = entry.get(suboption_entry)
        if suboptions:
            add_full_key(suboptions, suboption_entry=suboption_entry, _full_key=full_key_k)


def augment_docs(plugin_info: t.MutableMapping[str, t.MutableMapping[str, t.Any]]) -> None:
    """
    Add additional data to the data extracted from the plugins.

    The additional data is calculated from the existing data and then added to the data.
    Current Augmentations:

    * ``full_key`` allows displaying nested suboptions and return dicts.

    :arg plugin_info: The plugin_info that will be analyzed and augmented.

    .. warning:: This function operates by side-effect.  The plugin_info dictionay is modified
        directly.
    """
    for plugin_type, plugin_map in plugin_info.items():
        for plugin_name, plugin_record in plugin_map.items():
            add_full_key(plugin_record['return'], 'contains')
            add_full_key(plugin_record['doc']['options'], 'suboptions')
