Changelog YAML Format
=====================

This describes the format which is required from collections which want to be included in the Ansible Community Distribution if they want to have a nicely formatted changelog for their collection in the ACD combined changelog.

The format is similar to the `.changes.yaml` file used internally by Ansible until 2.9.x (see [here](https://github.com/ansible/ansible/blob/stable-2.9/changelogs/.changes.yaml) for an example). Concrete examples for collection changelogs with the new format described here can be found [here](https://github.com/felixfontein/ansible-versioning_test_collection/blob/master/changelogs/changelog.yaml) and [here](https://github.com/felixfontein/ansible-versioning_test_collection/blob/1.0.2/changelogs/changelog.yaml).

Please remember that collection versions **must** use [semantic versioning](https://semver.org/) if included in ACD or RedHat's Automation Hub.

You can use the `ansible-changelog` tool to validate these files:

    ansible-changelog lint-changelog /path/to/changelog.yaml

(This only works for `changelog.yaml` files in collections, not for the corresponding files in ansible-base, since ansible-base currently does not conform to semantic versioning.)


## changelog.yaml

The file must be named `changelogs.yaml` and stored in the `changelogs/` subdirectory of the collection root (i.e. the directory containing `galaxy.yml`). It must be a [YAML 1.1](https://yaml.org/spec/1.1/) file.

At the top level, there are two entries:

1. A string `ancestor`, which can also be `null` or omitted if the changelog has no ancestor.
2. A dictionary `releases`, which maps version numbers to release information.

If `ancestor` is a string, it must be an existing version of the collection which precedes all versions mentioned in this changelog. This is used when the changelog is truncated, for example when using release branches like for ansible-base. There, the `stable-2.10` branch's changelog contains only changelog entries for 2.10.x releases. Since the first 2.10.0b1 release contains all changes made to `devel` after `stable-2.9` was branched, the ancestor for the 2.10 changelog is `2.9.0b1`, the first release made after branching `stable-2.9`.

The following shows the outline of a `changelog.yaml` file with four versions:

```.yaml
ancestor: 0.5.4
releases:
  1.0.0-alpha:
    ...
  1.0.0-beta:
    ...
  1.0.0:
    ...
  1.0.1:
    ...
```

### Release information

For a release `x.y.z`, the `releases` dictionary contains an entry `x.y.z` mapping to another dictionary. That dictionary can have the following entries:

1. `codename`: a string for the version's codename. Optional; mainly required for ansible-base.
2. `fragments`: a list of strings mentioning changelog fragment files used for this release. This is not used for compiling a changelog.
3. `changes`: a dictionary containing all changes. See below.
4. `modules`: a list of plugin dictionaries. See below.
5. `plugins`: a dictionary mapping plugin types to lists of plugin dictionaries. See below.

The following is an example of release information for version `1.0.0`:

```.yaml
releases:
  1.0.0:
    codename: White Rabbit
    changes:
      release_summary: This is the initial White Rabbit release. Enjoy!
      major_changes:
        - The authentication method handling has been rewritten.
      minor_changes:
        - foo - Module can now reformat hard disks without asking.
        - bob lookup - Makes sure Bob isn't there multiple times.
      breaking_changes:
        - Due to the security bug in the post module, the module no longer accepts the password
          option. Please stop using the option and change any password you ever supplied to the
          module.
      deprecated_features:
        - foo - The bar option has been deprecated. Use the username option instead.
        - send_request - The quic option has been deprecated. Use the protocol option instead.
      removed_features:
        - foo - The baz option has been removed. It has never been used anyway.
      security_fixes:
        - post - The module accidentally sent your password in plaintext to all servers it could find.
      bugfixes:
        - post - The module made PUT requests instead of POST requests.
        - get - The module will no longer crash if it received invalid JSON data.
    modules:
      - name: head
        description: Make a HEAD request
        namespace: 'net_tools.rest'
      - name: echo
        description: Echo params
        namespace: ''
    plugins:
      lookup:
        - name: reverse
          description: Reverse magic
          namespace: null
      inventory:
        - name: docker
          description: Inventory plugin for docker containers
          namespace: null
```

#### Changes

The `changes` dictionary contains different sections of the changelog for this version.

1. `release_summary`: a string summarizing the release. Should not be long text.
2. `major_changes`: a list of strings describing major changes. A release should not have many major changes. The changes described here should be large changes affecting several modules, and be changes that the users should better be aware of.
3. `minor_changes`: a list of strings describing minor changes. A minor change could be adding a module or plugin option.
4. `breaking_changes`: a list of strings describing breaking changes. This should list all breaking changes (which are not deprecated or removed features) which every user *has* to read when upgrading to find out what they have to change in their playbooks and roles. This is mainly what used to be in the Porting Guide for older Ansible versions. This should only appear for major releases (x.0.0) and pre-releases.
5. `deprecated_features`: a list of strings describing features deprecated in this release. This should only appear for major (x.0.0) or minor (x.y.0) versions.
6. `removed_features`: a list of strings describing features removed in this release. The features should have been deprecated earlier. This should only appear for major releases (x.0.0) as these are breaking changes.
7. `security_fixes`: a list of strings describing security-relevant bugfixes. If available, they should include the issue's CVE.
8. `bugfixes`: a list of strings describing other bugfixes.

Note that not every section has to be used. Also note that the sections `deprecated_features` and `security_fixes` have been added only after Ansible 2.9.

Every of these sections - except `release_summary` - should contain a *list* of strings. Every string in this list, as well as the `release_summary` section itself, must be valid [reStructuredText](https://en.wikipedia.org/wiki/ReStructuredText). Every string should be one line only, except for `release_summary`.

The `changes` dictionary could look as follows:

```.yaml
releases:
  1.0.0:
    changes:
      release_summary: |
        This is the initial White Rabbit release. Enjoy!
      major_changes:
        - The authentication method handling has been rewritten.
      minor_changes:
        - foo - Module can now reformat hard disks without asking.
        - bob lookup - Makes sure Bob isn't there multiple times.
      breaking_changes:
        - Due to the security bug in the post module, the module no longer accepts the password
          option. Please stop using the option and change any password you ever supplied to the
          module.
      deprecated_features:
        - foo - The bar option has been deprecated. Use the username option instead.
        - send_request - The quic option has been deprecated. Use the protocol option instead.
      removed_features:
        - foo - The baz option has been removed. It has never been used anyway.
      security_fixes:
        - post - The module accidentally sent your password in plaintext to all servers it could find.
      bugfixes:
        - post - The module made PUT requests instead of POST requests.
        - get - The module will no longer crash if it received invalid JSON data.
```

#### Plugins and modules

The `modules` list should a be list of module plugin descriptions. The `plugins` dictionary should map plugin types to lists of plugin descriptions.

Currently valid plugin types are:
1. `become`
2. `cache`
3. `callback`
4. `cliconf`
5. `connection`
6. `httpapi`
7. `inventory`
8. `lookup`
9. `netconf`,
10. `shell`
11. `strategy`
12. `vars`

See `DOCUMENTABLE_PLUGINS` in https://github.com/ansible/ansible/blob/devel/lib/ansible/constants.py for a complete list of plugin types (minus `modules`).

For every module or plugin, the description is a dictionary with the following keys:

1. `name`: the name of the module resp. plugin. It must not be the FQCN, but the name inside the collection.
2. `description`: the value of `short_description` in the module's resp. plugin's `DOCUMENTATION`.
3. `namespace`: must be `null` for plugins. For modules, must be `''` for modules directly in `plugins/modules/`, or the dot-separated list of directories the module is in inside the `plugins/modules/` directory. This is mostly relevant for large collections such as community.general and community.network. For example, the `community.general.docker_container` module is in the directory `plugins/modules/cloud/docker/`, hence its namespace must be `cloud.docker`. The namespace is used to group new modules by their namespace inside the collection.

The `modules` list and `plugins` dictionary could look as follows:

```.yaml
releases:
  1.0.0:
    modules:
      - name: head
        description: Make a HEAD request
        namespace: 'net_tools.rest'
      - name: echo
        description: Echo params
        namespace: ''
    plugins:
      lookup:
        - name: reverse
          description: Reverse magic
          namespace: null
      inventory:
        - name: docker
          description: Inventory plugin for docker containers
          namespace: null
```
