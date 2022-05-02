## antsibull: build-release

An Ansible role that builds an Ansible release package with Antsibull and tests it.

### Requirements

- ansible-core to run this role
- antsibull needs build Ansible
- git to checkout ansible-build-data and ansible repositories

### Variables

See [defaults/main.yaml](https://github.com/ansible-community/antsibull/blob/master/roles/build-release/defaults/main.yaml)

### Example playbook

Build what is probably the latest release (provided by role defaults):

```yaml
- name: Build an Ansible release with role defaults
  hosts: localhost
  gather_facts: no
  roles:
    - build-release
```

To re-build a specific version with some additional settings and a forked ansible-build-data:
```yaml
- name: Build a specific Ansible release with a forked ansible-build-data
  hosts: localhost
  gather_facts: no
  vars:
    antsibull_ansible_version: 4.10.10
    antsibull_data_git_repo: https://github.com/dmsimard/ansible-build-data
    antsibull_data_version: 4.10.10-branch
    antsibull_force_rebuild: true
  roles:
    - build-release
```
