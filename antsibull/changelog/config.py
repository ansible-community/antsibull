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

from typing import Mapping, Optional

import yaml

from .errors import ChangelogError
from .logger import LOGGER


class PathsConfig:
    """
    Configuration for paths.
    """

    is_collection: bool

    base_dir: str
    galaxy_path: Optional[str]
    changelog_dir: str
    config_path: str
    ansible_doc_path: Optional[str]

    @staticmethod
    def _changelog_dir(base_dir: str) -> str:
        return os.path.join(base_dir, 'changelogs')

    @staticmethod
    def _config_path(changelog_dir: str) -> str:
        return os.path.join(changelog_dir, 'config.yaml')

    def __init__(self, is_collection: bool, base_dir: str, galaxy_path: Optional[str],
                 ansible_doc_path: Optional[str]):
        """
        Forces configuration with given base path.

        :arg base_dir: Base directory of Ansible checkout or collection checkout
        :arg galaxy_path: Path to galaxy.yml for collection checkouts
        :arg ansible_doc_path: Path to ``ansible-doc``
        """
        self.is_collection = is_collection
        self.base_dir = base_dir
        if galaxy_path and not os.path.exists(galaxy_path):
            LOGGER.debug('Cannot find galaxy.yml')
            galaxy_path = None
        self.galaxy_path = galaxy_path
        self.changelog_dir = PathsConfig._changelog_dir(self.base_dir)
        self.config_path = PathsConfig._config_path(self.changelog_dir)
        self.ansible_doc_path = ansible_doc_path

    @staticmethod
    def force_collection(base_dir: str) -> 'PathsConfig':
        """
        Forces configuration for collection checkout with given base path.

        :arg base_dir: Base directory of collection checkout
        """
        base_dir = os.path.abspath(base_dir)
        return PathsConfig(True, base_dir, os.path.join(base_dir, 'galaxy.yml'), None)

    @staticmethod
    def force_ansible(base_dir: str) -> 'PathsConfig':
        """
        Forces configuration with given Ansible Base base path.

        :type base_dir: Base directory of ansible-base checkout
        """
        base_dir = os.path.abspath(base_dir)
        return PathsConfig(False, base_dir, None, None)

    @staticmethod
    def detect(is_collection: Optional[bool] = None) -> 'PathsConfig':
        """
        Detect paths configuration from current working directory.

        :raises ValueError: cannot identify collection or ansible-base checkout
        """
        previous: Optional[str] = None
        base_dir = os.getcwd()
        while True:
            changelog_dir = PathsConfig._changelog_dir(base_dir)
            config_path = PathsConfig._config_path(changelog_dir)
            if os.path.exists(changelog_dir) and os.path.exists(config_path):
                galaxy_path = os.path.join(base_dir, 'galaxy.yml')
                if os.path.exists(galaxy_path) or is_collection is True:
                    # We are in a collection and assume ansible-doc is available in $PATH
                    return PathsConfig(True, base_dir, galaxy_path, 'ansible-doc')
                ansible_lib_dir = os.path.join(base_dir, 'lib', 'ansible')
                if os.path.exists(ansible_lib_dir) or is_collection is False:
                    # We are in a checkout of ansible/ansible
                    return PathsConfig(
                        False, base_dir, None,
                        os.path.join(base_dir, 'bin', 'ansible-doc'))
            previous, base_dir = base_dir, os.path.dirname(base_dir)
            if previous == base_dir:
                raise ValueError('Cannot identify collection or ansible-base checkout.')


def load_galaxy_metadata(paths: PathsConfig) -> dict:
    """
    Load galaxy.yml metadata.

    :arg paths: Paths configuration.
    :return: The contents of ``galaxy.yaml``.
    """
    path = paths.galaxy_path
    if path is None:
        raise ValueError('Cannot find galaxy.yml')
    with open(path, 'r') as galaxy_fd:
        return yaml.safe_load(galaxy_fd)


class CollectionDetails:
    """
    Stores information about a collection. Can auto-populate from galaxy.yml.
    """

    paths: PathsConfig
    galaxy_yaml_loaded: bool

    namespace: Optional[str]
    name: Optional[str]
    version: Optional[str]
    flatmap: Optional[bool]

    def __init__(self, paths: PathsConfig):
        self.paths = paths
        self.galaxy_yaml_loaded = False
        self.namespace = None
        self.name = None
        self.version = None
        self.flatmap = None

    def _parse_galaxy_yaml(self, galaxy_yaml):
        self.galaxy_yaml_loaded = True
        if self.namespace is None and isinstance(galaxy_yaml.get('namespace'), str):
            self.namespace = galaxy_yaml.get('namespace')
        if self.name is None and isinstance(galaxy_yaml.get('name'), str):
            self.name = galaxy_yaml.get('name')
        if self.version is None and isinstance(galaxy_yaml.get('version'), str):
            self.version = galaxy_yaml.get('version')
        if self.flatmap is None:
            self.flatmap = galaxy_yaml.get('type', '') == 'flatmap'

    def _load_galaxy_yaml(self, needed_var: str,
                          what_for: Optional[str] = None,
                          help_text: Optional[str] = None):
        if self.galaxy_yaml_loaded:
            return
        if not self.paths.is_collection:
            raise Exception('Internal error: cannot get collection details for non-collection')

        if what_for is None:
            what_for = 'load field "{0}"'.format(needed_var)
        try:
            galaxy_yaml = load_galaxy_metadata(self.paths)
        except Exception as e:
            msg = 'Cannot find galaxy.yaml to {0}: {1}'.format(what_for, e)
            if help_text is not None:
                msg = '{0}. {1}'.format(msg, help_text)
            raise ChangelogError(msg)

        self._parse_galaxy_yaml(galaxy_yaml)

    def get_namespace(self) -> str:
        """
        Get collection's namespace.
        """
        help_text = 'You can explicitly specify the value with `--collection-namespace`.'
        if self.namespace is None:
            self._load_galaxy_yaml('namespace', help_text=help_text)
        namespace = self.namespace
        if namespace is None:
            raise ChangelogError('Cannot find "namespace" field in galaxy.yaml. ' + help_text)
        return namespace

    def get_name(self) -> str:
        """
        Get collection's name.
        """
        help_text = 'You can explicitly specify the value with `--collection-name`.'
        if self.name is None:
            self._load_galaxy_yaml('name', help_text=help_text)
        name = self.name
        if name is None:
            raise ChangelogError('Cannot find "name" field in galaxy.yaml. ' + help_text)
        return name

    def get_version(self) -> str:
        """
        Get collection's version.
        """
        help_text = 'You can explicitly specify the value with `--version`.'
        if self.version is None:
            self._load_galaxy_yaml('version', help_text=help_text)
        version = self.version
        if version is None:
            raise ChangelogError('Cannot find "version" field in galaxy.yaml. ' + help_text)
        return version

    def get_flatmap(self) -> bool:
        """
        Get collection's flatmap flag.
        """
        help_text = 'You can explicitly specify the value with `--collection-flatmap`.'
        if self.flatmap is None:
            self._load_galaxy_yaml('type', what_for='determine flatmapping', help_text=help_text)
        flatmap = self.flatmap
        if flatmap is None:
            raise Exception(
                'Internal error: flatmap is None after successful _load_galaxy_yaml() call')
        return flatmap


class ChangelogConfig:
    # pylint: disable=too-many-instance-attributes
    """
    Configuration for changelogs.
    """

    paths: PathsConfig
    collection_details: CollectionDetails

    config: dict
    is_collection: bool
    title: Optional[str]
    notes_dir: str
    prelude_name: str
    prelude_title: str
    new_plugins_after_name: str
    changes_file: str
    changes_format: str
    keep_fragments: bool
    changelog_filename_template: str
    changelog_filename_version_depth: int
    mention_ancestor: bool
    trivial_section_name: str
    release_tag_re: str
    pre_release_tag_re: str
    sections: Mapping[str, str]

    def __init__(self, paths: PathsConfig, collection_details: CollectionDetails, config: dict):
        """
        Create changelog config from dictionary.
        """
        self.paths = paths
        self.collection_details = collection_details
        self.config = config

        self.is_collection = paths.is_collection
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
        self.trivial_section_name = self.config.get('trivial_section_name', 'trivial')

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

        sections = collections.OrderedDict([(self.prelude_name, self.prelude_title)])
        for section_name, section_title in self.config['sections']:
            sections[section_name] = section_title
        self.sections = sections

    def store(self) -> None:
        """
        Store changelog configuration file to disk.
        """
        config: dict = {
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
            'trivial_section_name': self.trivial_section_name,
        }
        if not self.is_collection:
            config.update({
                'release_tag_re': self.release_tag_re,
                'pre_release_tag_re': self.pre_release_tag_re,
            })
        if self.title is not None:
            config['title'] = self.title
        sections = []
        for key, value in self.sections.items():
            if key == self.prelude_name and value == self.prelude_title:
                continue
            sections.append([key, value])
        config['sections'] = sections

        with open(self.paths.config_path, 'w') as config_f:
            yaml.safe_dump(config, config_f, default_flow_style=False, encoding='utf-8')

    @staticmethod
    def load(paths: PathsConfig, collection_details: CollectionDetails) -> 'ChangelogConfig':
        """
        Load changelog configuration file from disk.
        """
        with open(paths.config_path, 'r') as config_fd:
            config = yaml.safe_load(config_fd)
        return ChangelogConfig(paths, collection_details, config)

    @staticmethod
    def default(paths: PathsConfig, collection_details: CollectionDetails,
                title: Optional[str] = None) -> 'ChangelogConfig':
        """
        Create default changelog config.

        :type title: Title of the project
        """
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
        return ChangelogConfig(paths, collection_details, config)
