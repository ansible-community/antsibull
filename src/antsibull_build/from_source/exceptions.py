# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Errors related to the from_source package
"""

from __future__ import annotations


class CloneError(Exception):
    """
    An issue occured with cloning a collection's upstream repository
    """

    def __init__(self, message: str, collection: str) -> None:
        self.message = message
        self.collection = collection
        super().__init__(f"{self.collection}: {self.message}")


__all__ = ("CloneError",)
