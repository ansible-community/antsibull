# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020

"""
Entrypoint to the antsibull-changelog script.
"""

from __future__ import annotations

import sys


def run(args: list[str]) -> int:  # pylint: disable=unused-argument
    """
    Main program entry point.
    """
    print(
        'WARNING: `antsibull-lint` is deprecated. Use `antsibull-changelog lint-changelog-yaml`'
        ' or `antsibull-docs lint-collection-docs` depending on your use-case.',
        file=sys.stderr)
    return 2


def main() -> int:
    """
    Entrypoint called from the script.

    console_scripts call functions which take no parameters.  However, it's hard to test a function
    which takes no parameters so this function lightly wraps :func:`run`, which actually does the
    heavy lifting.

    :returns: A program return code.

    Return codes:
        :0: Success
        :1: Unhandled error.  See the Traceback for more information.
        :2: There was a problem with the command line arguments
        :3: Linting failed
        :4: Needs to be run on a newer version of Python
    """
    if sys.version_info < (3, 6):
        print('Needs Python 3.6 or later')
        return 4

    return run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
