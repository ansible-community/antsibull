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
FQCN_STRICT_RE = re.compile(
    fr'({NAMESPACE_RE_STR})\.({NAMESPACE_RE_STR})\.({NAMESPACE_RE_STR}(?:\.{NAMESPACE_RE_STR})*)')

# FQCN_RE and FQCN_STRICT_RE match certain Fully Qualified Collection Names. FQCN_RE is more liberal
# than FQCN_STRICT_RE and allows random characters after the namespace and collection name, while
# FQCN_STRICT_RE is closer to the definition in Ansible. We use FQCN the same as the term FQCR
# (Fully Qualified Collection Reference) is used in Ansible.
#
# The set of possible FQCRs accepted by Ansible is defined in
# https://github.com/ansible/ansible/blob/devel/lib/ansible/utils/collection_loader/_collection_finder.py#L662
# similarly to what we define as FQCN_STRICT_RE, except that it allows arbitrary words matching
# '[a-zA-Z0-9_]+' instead of words matching NAMESPACE_RE_STR.
#
# The following table shows some differences and similarities:
#
# String               FQCN_RE  FQCN_STRICT_RE  Ansible FQCR
# ----------------------------------------------------------
# 'a.b.c'              yes      yes             yes
# 'a.b.c.d'            yes      yes             yes
# 'a.b.c-d'            yes      no              no
# 'A.B.C'              no       no              yes
# 'a..c'               no       no              no


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


def is_fqcn(value: str) -> bool:
    """
    Return whether ``value`` is a Fully Qualified Collection Name (FQCN).

    :arg value: The value to test.
    :returns: ``True`` if the value is a FQCN, ``False`` if it is not.
    """
    return bool(FQCN_STRICT_RE.match(value))
