# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2023
"""Helper to create a Galaxy context."""

from __future__ import annotations

import aiohttp
from antsibull_core.galaxy import GalaxyContext


async def create_galaxy_context() -> GalaxyContext:
    """
    Create a Galaxy context.
    """
    async with aiohttp.ClientSession(trust_env=True) as aio_session:
        return await GalaxyContext.create(aio_session)
