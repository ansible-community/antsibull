# Copyright (C) 2021 David Moreau-Simard <dmsimard@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import yaml
import ansible
from ansible.plugins.action import ActionBase

DEFAULT_RUNTIME = "%s/config/ansible_builtin_runtime.yml" % os.path.dirname(ansible.__file__)

DOCUMENTATION = """
---
module: parse_ansible_runtime
short_description: Parses an ansible_builtin_runtime.yml file for testing purposes.
version_added: "2.12"
author: "David Moreau-Simard <dmsimard@redhat.com>"
description:
    - Parses an ansible_builtin_runtime.yml file for testing purposes.
options:
    runtime_file:
        description:
            - Path to an ansible_builtin_runtime.yml file
            - If not set, the module will default to the one for the currently-running Ansible process.
        required: false
"""

EXAMPLES = """
- name: Parse the runtime currently used by Ansible
  parse_ansible_runtime:
  register: _parsed_runtime

- name: Parse a specific runtime configuration file
  parse_ansible_runtime:
    runtime_file: /opt/git/ansible/lib/ansible/config/ansible_builtin_runtime.yml
  register: _parsed_runtime

- name: List parsed collections
  debug:
    msg: "{{ item }}"
  loop: "{{ _parsed_runtime.collections }}"

- name: List parsed modules (redirection targets)
  debug:
    msg: "{{ item }}"
  loop: "{{ _parsed_runtime.modules }}"
"""

RETURN = """
collections:
    description: List of collection names found in module redirections
    returned: on success
    type: list
    sample: ['community.crypto', 'community.general']
modules:
    description: List of module names found in module redirections
    returned: on success
    type: list
    sample: ['community.general.ovirt', 'community.general.proxmox']
"""


class ActionModule(ActionBase):
    """ Parses an Ansible runtime file from the Ansible controller """

    TRANSFERS_FILES = False

    def __init__(self, *args, **kwargs):
        super(ActionModule, self).__init__(*args, **kwargs)

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        runtime_file = self._task.args.get("runtime_file", DEFAULT_RUNTIME)
        runtime = yaml.safe_load(open(runtime_file, "r"))

        # TODO: Add other verifiable plugin types
        collections = []
        modules = []
        for module, target in runtime["plugin_routing"]["modules"].items():
            if "redirect" in target:
                collections.append(".".join(target["redirect"].split('.')[:-1]))
                modules.append(target["redirect"])

        result["collections"] = sorted(list(set(collections)))
        result["modules"] = sorted(list(set(modules)))
        result["changed"] = False
        result["msg"] = "Parsed %s successfully" % runtime_file

        return result
