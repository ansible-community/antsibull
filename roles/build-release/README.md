## antsibull: build-release

An Ansible role that builds an Ansible release package with Antsibull and tests it.

### Requirements

This role is expected to run directly from an antsibull git repository checkout.

Otherwise:

- ansible-base to run this role
- poetry to install and run antsibull
- git to checkout ansible-build-data and ansible repositories

### Variables

See [defaults/main.yaml](https://github.com/ansible-community/antsibull/blob/master/roles/build-release/defaults/main.yaml)

### Example playbook

Build what is probably the latest release (provided by role defaults):

```yaml
- name: Build an Ansible release
  hosts: localhost
  gather_facts: yes
  roles:
    - build-release
```
