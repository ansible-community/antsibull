**************************
Changelogs for Collections
**************************

The ``antsibull-changelog`` tool allows you to create and update changelogs for Ansible collections, that are similar to the ones provided by Ansible itself in earlier versions, and that are compatible to the combined Ansible Community Distribution changelogs.

The following instructions assume that antsibull has been properly installed, for example via ``pip install https://github.com/ansible-community/ansible-changelog/archive/master.tar.gz``. If it is used with ``poetry`` from git, ``antsibull-changelog`` has to be replaced with ``poetry run antsibull-changelog``.

Bootstrapping changelogs for collections
========================================

To set up ``antsibull-changelog``, run::

    antsibull-changelog init /path/to/your/collection

This is the directory which contains ``galaxy.yml``. This creates subdirectories ``changelogs/`` and ``changelogs/fragments/``, and a configuration file ``changelogs/config.yaml``. Adjust the configuration file to your needs. The settings of highest interest are:

1. ``title``: This is by default the titlecase of your collection's namespace and name. Feel free to insert a nicer name here.
2. ``keep_fragments``: The default value ``false`` removes the fragment files after a release is done. If you prefer to keep fragment files for older releases, set this to ``true``.

Validating changelog fragments
==============================

If you want to do a basic syntax check of changelog fragments, you can run::

    antsibull-changelog lint

If you want to check a specific fragment, you can provide a path to it; otherwise, all fragments in ``changelogs/fragments/`` are checked. This can be used in CI to avoid contributors to check in invalid changelog fragments, or introduce new sections (by mistyping existing ones, or simply guessing wrong names).

If ``antsibull-changelog lint`` produces no output on stdout, and exits with exit code 0, the changelog fragments are OK. If errors are found, they are reported by one line in stdout for each error in the format ``path/to/fragment:line:column:message``, and the program exits with exit code 3. Other exit codes indicate problems with the command line or during the execution of the linter.

Releasing a new version of a collection
=======================================

To release a new version of a collection, you need to run::

    antsibull-changelog release

inside your collection's tree. This assumes that ``galaxy.yml`` exists and its version is the version of the release you want to make. If that file does not exist, or has a wrong value for ``version``, you can explicitly specify the version you want to release::

    antsibull-changelog release --version 1.0.0

You can also specify a release date with ``--date 2020-12-31``, if the default (today) is not what you want.

When doing a release, the changelog generator will read all changelog fragments which are not already mentioned in the changelog, and include them in a new entry in ``changelogs/changelog.yaml``. It will also scan metadata for all modules and plugins of your collection, and mention all modules and plugins with ``version_added`` equal to this version as new modules/plugins.

The metadata for modules and plugins is stored in ``changelogs/.plugin-cache.yaml``, and is only recalculated once the release version changes. To force recollecting this data, either delete the file, or specify the ``--reload-plugins`` option to ``antsibull-changelog release``.

After running ``antsibull-changelog release``, you should check ``changelogs/changelog.yaml`` and the generated reStructuredText file (by default ``changelogs/CHANGELOG.rst``) in.

Changelog Fragment Categories
=============================

This section describes the section categories created in the default config. You can change them, though this is strongly discouraged for collections which will be included in the Ansible Community Distribution.

The categories are very similar to the ones in the `Ansible-base changelog fragments <https://docs.ansible.com/ansible/latest/community/development_process.html#changelogs-how-to>`_. In fact, they are the same, except that there are three new categories: ``breaking_changes``, ``security_fixes`` and ``trivial``.

The full list of categories is:

**release_summary**
  This is a special section: as opposed to a list of strings, it accepts one string. This string will be inserted at the top of the changelog entry for the current version, before any section. There can only be one fragment with a ``release_summary`` section. In Ansible-base, this is used for stating the release date and for linking to the porting guide (`example <https://github.com/ansible/ansible/blob/stable-2.9/changelogs/fragments/v2.9.0_summary.yaml>`_, `result <https://github.com/ansible/ansible/blob/stable-2.9/changelogs/CHANGELOG-v2.9.rst#id23>`_).

**breaking_changes**
  This (new) category should list all changes to features which absolutely require attention from users when upgrading, because an existing behavior is changed. This is mostly what Ansible's Porting Guide used to describe. This section should only appear in a initial major release (`x.0.0`) according to semantic versioning.

**major_changes**
  This category contains major changes to the collection. It should only contain a few items per major version, describing high-level changes. This section should not appear in patch releases according to semantic versioning.

**minor_changes**
  This category should mention all new features, like plugin or module options. This section should not appear in patch releases according to semantic versioning.

**removed_features**
  This category should mention all modules, plugins and features that have been removed in this release. This section should only appear in a initial major release (`x.0.0`) according to semantic versioning.

**deprecated_features**
  This category should contain all modules, plugins and features which have been deprecated and will be removed in a future release. This section should not appear in patch releases according to semantic versioning.

**security_fixes**
  This category should mention all security relevant fixes, including CVEs if available.

**bugfixes**
  This category should be a list of all bug fixes which fix a bug that was present in a previous version.

**known_issues**
  This category should mention known issues that are currently not fixed or will not be fixed.

**trivial**
  This category will **not be shown** in the changelog. It can be used to describe changes that are not touching user-facing code, like changes in tests. This is useful if every PR is required to have a changelog fragment.
