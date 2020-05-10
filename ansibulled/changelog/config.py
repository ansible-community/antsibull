# -*- coding: utf-8 -*-
# Author: Matt Clay <matt@mystile.com>
# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Configuration classes for paths and changelogs.
"""

import collections
import os

import yaml


class PathsConfig:
    """Configuration for paths."""

    @staticmethod
    def _changelog_dir(base_dir):
        return os.path.join(base_dir, 'changelogs')

    @staticmethod
    def _config_path(changelog_dir):
        return os.path.join(changelog_dir, 'config.yaml')

    def __init__(self, base_dir, galaxy_path, ansible_doc_path):
        """Forces configuration with given base path.
        :type base_dir: str
        :type galaxy_path: str | None
        :type ansible_doc_path: str | None
        """
        self.base_dir = base_dir
        self.galaxy_path = galaxy_path
        self.changelog_dir = PathsConfig._changelog_dir(self.base_dir)
        self.config_path = PathsConfig._config_path(self.changelog_dir)
        self.ansible_doc_path = ansible_doc_path

    @staticmethod
    def force_collection(base_dir):
        """Forces configuration with given collection base path.
        :type base_dir: str
        """
        base_dir = os.path.abspath(base_dir)
        return PathsConfig(base_dir, os.path.join(base_dir, 'galaxy.yml'), None)

    @staticmethod
    def force_ansible(base_dir):
        """Forces configuration with given Ansible Base base path.
        :type base_dir: str
        """
        base_dir = os.path.abspath(base_dir)
        return PathsConfig(base_dir, None, None)

    @staticmethod
    def detect():
        """Detect paths configuration from current working directory.
        :raises ValueError: cannot identify collection or ansible/ansible checkout
        """
        previous = None
        base_dir = os.getcwd()
        while True:
            changelog_dir = PathsConfig._changelog_dir(base_dir)
            config_path = PathsConfig._config_path(changelog_dir)
            if os.path.exists(changelog_dir) and os.path.exists(config_path):
                galaxy_path = os.path.join(base_dir, 'galaxy.yml')
                if os.path.exists(galaxy_path):
                    # We are in a collection and assume ansible-doc is available in $PATH
                    return PathsConfig(base_dir, galaxy_path, 'ansible-doc')
                if os.path.exists(os.path.join(base_dir, 'lib', 'ansible')):
                    # We are in a checkout of ansible/ansible
                    return PathsConfig(base_dir, None, os.path.join(base_dir, 'bin', 'ansible-doc'))
            previous, base_dir = base_dir, os.path.dirname(base_dir)
            if previous == base_dir:
                raise ValueError()


class ChangelogConfig:
    """Configuration for changelogs."""
    def __init__(self, is_collection, config):
        """
        :type config: dict
        """
        self.config = config

        self.is_collection = is_collection
        self.title = self.config.get('title')
        self.notes_dir = self.config.get('notesdir', 'fragments')
        self.prelude_name = self.config.get('prelude_section_name', 'release_summary')
        self.prelude_title = self.config.get('prelude_section_title', 'Release Summary')
        self.new_plugins_after_name = self.config.get('new_plugins_after_name', '')  # not used
        self.changes_file = self.config.get('changes_file', '.changes.yaml')
        self.changes_format = self.config.get('changes_format', 'classic')
        self.keep_fragments = self.config.get('keep_fragments', self.changes_format == 'classic')
        self.changelog_filename_template = self.config.get(
            'changelog_filename_template', 'CHANGELOG-v%s.rst')
        self.changelog_filename_version_depth = self.config.get(
            'changelog_filename_version_depth', 2)
        self.mention_ancestor = self.config.get('mention_ancestor', True)

        # The following are only relevant for ansible-base:
        self.release_tag_re = self.config.get(
            'release_tag_re', r'((?:[\d.ab]|rc)+)')
        self.pre_release_tag_re = self.config.get(
            'pre_release_tag_re', r'(?P<pre_release>\.\d+(?:[ab]|rc)+\d*)$')

        if self.changes_format not in ('classic', 'combined'):
            raise ValueError('changes_format must be one of "classic" and "combined"')
        if self.changes_format == 'classic' and not self.keep_fragments:
            raise ValueError('changes_format == "classic" cannot be '
                             'combined with keep_fragments == False')

        self.sections = collections.OrderedDict([(self.prelude_name, self.prelude_title)])

        for section_name, section_title in self.config['sections']:
            self.sections[section_name] = section_title

    def store(self, path):
        """
        :type path: str
        """
        config = {
            'notesdir': self.notes_dir,
            'changes_file': self.changes_file,
            'changes_format': self.changes_format,
            'mention_ancestor': self.mention_ancestor,
            'keep_fragments': self.keep_fragments,
            'changelog_filename_template': self.changelog_filename_template,
            'changelog_filename_version_depth': self.changelog_filename_version_depth,
            'prelude_section_name': self.prelude_name,
            'prelude_section_title': self.prelude_title,
            'new_plugins_after_name': self.new_plugins_after_name,
            'sections': [],
        }
        if not self.is_collection:
            config.update({
                'release_tag_re': self.release_tag_re,
                'pre_release_tag_re': self.pre_release_tag_re,
            })
        if self.title is not None:
            config['title'] = self.title
        for k, v in self.sections.items():
            if k == self.prelude_name and v == self.prelude_title:
                continue
            config['sections'].append([k, v])

        with open(path, 'wb') as f:
            yaml.safe_dump(config, f, default_flow_style=False, encoding='utf-8')

    @staticmethod
    def load(path, is_collection):
        """
        :type path: str
        :type is_collection: bool
        """
        with open(path, 'r') as config_fd:
            config = yaml.safe_load(config_fd)
        return ChangelogConfig(is_collection, config)

    @staticmethod
    def default(title=None, is_collection=True):
        config = {
            'changes_file': 'changelog.yaml',
            'changes_format': 'combined',
            'changelog_filename_template': 'CHANGELOG.rst',
            'changelog_filename_version_depth': 0,
            'new_plugins_after_name': 'removed_features',
            'sections': [
                ['major_changes', 'Major Changes'],
                ['minor_changes', 'Minor Changes'],
                ['breaking_changes', 'Breaking Changes / Porting Guide'],
                ['deprecated_features', 'Deprecated Features'],
                ['removed_features', 'Removed Features (previously deprecated)'],
                ['security_fixes', 'Security Fixes'],
                ['bugfixes', 'Bugfixes'],
                ['known_issues', 'Known Issues'],
            ],
        }
        if title is not None:
            config['title'] = title
        return ChangelogConfig(is_collection, config)
