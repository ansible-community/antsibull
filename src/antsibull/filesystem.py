# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Entrypoint to the antsibull-docs script."""

import sh

try:
    # We fallback to /usr/bin/getfacl so we can ignore failure to import this
    import posix1e  # pyre-ignore[21]
except ImportError:
    posix1e = None


class UnableToCheck(Exception):
    """No library or command support to check this."""


class CheckFailure(Exception):
    """We checking failed unexpectedly."""


def _get_acls(path: str) -> str:
    """Return the acls for a given file or raise an exception."""
    acls = None
    if posix1e:
        acl = posix1e.ACL(file=path)
        acls = acl.to_any_text(options=posix1e.TEXT_NUMERIC_IDS).decode('utf-8')
    else:
        try:
            # sh dynamically creates functions which map to executables
            # pyre-ignore[16]
            acls = sh.getfacl(path, '-n').stdout.decode('utf-8')  # pylint:disable=no-member
        except sh.CommandNotFound:
            pass
        except Exception as e:
            # pylint:disable-next=raise-missing-from
            raise CheckFailure(f'Error while trying to get acls for {path}: {e}')

    if not acls:
        raise UnableToCheck(f'No way to determine acls for {path}')

    return acls


def writable_via_acls(path: str, euid: int) -> bool:
    """
    Check whether acls gives someone other than the user write access to a path.

    :arg path: Pathname to check.
    :arg euid: userid to identify the user by.
    :returns: True if acls give someone other than the user path write access to the path.
    """
    # Check acls if available
    acls = _get_acls(path)

    mask_has_write = True
    principal_has_write = False

    # Strip comments and blank lines.  Everything else is an acl
    for acl in (a for a in acls.splitlines() if not a.startswith('#') and a):
        type_, principal, permissions = acl.rsplit(':', 2)
        # default acls have the same issues as acls directly on the directory
        if type_.startswith('default:'):
            dummy_, type_ = type_.split(':', 1)

        # All the safe things:

        # ACL is for the user themselves
        if type_ == 'user' and (not principal or principal == euid):
            continue

        if type_ == 'mask':
            # The mask does not allow acls to set write
            if 'w' not in permissions:
                mask_has_write = False
                break
            # No other mask values affect safety
            continue

        # The acl doesn't grant write permission
        if 'w' not in permissions:
            continue

        # Okay, the principal has write in this case
        principal_has_write = True

    if mask_has_write and principal_has_write:
        return True
    return False
