# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""
Functions for parsing fully qualified collection names.

Some definitions:

:Fully qualified collection names: aka FQCN are the complete name for a collection.  They
    include the namespace, collection name, and the plugin name.  If a plugin is within a python
    package within the collection dir, then the FQCN may include that as well.
:short_name: The pieces of the fqcn that don't include the namespace and collection name.  If the
    `collections:` keyword is used in an ansible playbook to get shorter names, the short name is
    what users would have to specify.
"""

import re
import typing as t


#: Format that a collection namespace and collection name must follow
NAMESPACE_RE_STR = '[a-z0-9][a-z0-9_]+'
#: Format of a FQCN
FQCN_RE = re.compile(fr'({NAMESPACE_RE_STR})\.({NAMESPACE_RE_STR})\.(.*)')


def get_fqcn_parts(fqcn: str) -> t.Tuple[str, str, str]:
    """
    Parse a fqcn into its three parts.

    :arg fqcn: The fqcn string.
    :returns: A tuple of (namespace, collection name, plugin short_name).
    :raises ValueError: If the string could not be parsed into fqcn components.
    """
    match = FQCN_RE.match(fqcn)
    if not match:
        raise ValueError(f'{fqcn} could not be parsed into fqcn parts')
    return match.groups()
