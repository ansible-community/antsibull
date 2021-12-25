# Copyright: (c) 2019, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Jinja2 tests for use in Ansible documentation."""

import warnings
from functools import partial

from packaging.version import Version as PypiVer
from semantic_version import Version as SemVer

from ..vendored.collections import is_sequence


# if a module is added in a version of Ansible older than this, don't print the version added
# information in the module documentation because everyone is assumed to be running something newer
# than this already.
TOO_OLD_TO_BE_NOTABLE = '0.0.0'

test_list = partial(is_sequence, include_strings=False)


def still_relevant(version, cutoff=TOO_OLD_TO_BE_NOTABLE, collection=None):
    """
    Calculates whether the given version is older than a cutoff value

    :arg version: Version to check
    :arg cutoff: Calculate whether `version` is older than this
    :returns: True if the `version` is older than `cutoff` otherwise True.

    .. note:: This is similar to the ansible `version_compare` test but needs to handle the
        `historical` version and empty version.
    """
    # Note: This was the opposite in previous code but then the version_added was stripped out by
    # other things
    if not version:
        return False

    if version == 'historical':
        return False

    if collection == 'ansible.builtin':
        Version = PypiVer
    elif collection is not None:
        Version = SemVer
    else:
        # This used to be distutils.version.LooseVersion
        Version = PypiVer

    try:
        version = Version(version)
    except ValueError as e:
        warnings.warn(f"Could not parse {version}: {e}")
        return True
    try:
        return version >= Version(cutoff)
    except Exception as e:  # pylint:disable=broad-except
        warnings.warn(f"Could not compare {version}: {e}")
        return True
