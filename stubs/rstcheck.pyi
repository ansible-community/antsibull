# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Ansible Project, 2020

import docutils.utils


def check(source: str,
          filename: str = ...,
          report_level: docutils.utils.Reporter = ...,
          ignore: dict | None = ...,
          debug: bool = ...) -> list[tuple[int, str]]: ...
