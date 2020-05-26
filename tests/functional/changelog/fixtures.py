import os
import pathlib

import pytest
import yaml

from antsibull.cli.antsibull_changelog import run as run_changelog_tool
from antsibull.changelog.config import PathsConfig, CollectionDetails, ChangelogConfig

from typing import Any, Dict, List, Tuple, Optional, Set, Union


class Differences:
    added_dirs: List[str]
    added_files: List[str]
    removed_dirs: List[str]
    removed_files: List[str]
    changed_files: List[str]
    file_contents: Dict[str, bytes]
    file_differences: Dict[str, Tuple[bytes, bytes]]

    def __init__(self):
        self.added_dirs = []
        self.added_files = []
        self.removed_dirs = []
        self.removed_files = []
        self.changed_files = []
        self.file_contents = dict()
        self.file_differences = dict()

    def sort(self):
        self.added_dirs.sort()
        self.added_files.sort()
        self.removed_dirs.sort()
        self.removed_files.sort()
        self.changed_files.sort()

    def parse_yaml(self, path):
        return yaml.load(self.file_contents[path], Loader=yaml.SafeLoader)


class ChangelogEnvironment:
    base_path: pathlib.Path

    paths: PathsConfig
    config: ChangelogConfig

    created_dirs: Set[str]
    created_files: Dict[str, bytes]

    def __init__(self, base_path: pathlib.Path, paths: PathsConfig, is_collection: bool):
        self.base = base_path

        self.paths = paths
        self.config = ChangelogConfig.default(paths, CollectionDetails(paths))

        self.created_dirs = set()
        self.created_files = dict()

    def _write(self, path: str, data: bytes):
        with open(path, 'wb') as f:
            f.write(data)
        self.created_files[path] = data

    def _write_yaml(self, path: str, data: Any):
        self._write(path, yaml.dump(data, Dumper=yaml.SafeDumper).encode('utf-8'))

    def _written(self, path: str):
        with open(path, 'rb') as f:
            data = f.read()
        self.created_files[path] = data

    def set_plugin_cache(self, version: str, plugins: Dict[str, Dict[str, Dict[str, str]]]):
        data = {
            'version': version,
            'plugins': plugins,
        }
        config_dir = self.paths.changelog_dir
        os.makedirs(config_dir, exist_ok=True)
        self.created_dirs.add(config_dir)
        self._write_yaml(os.path.join(config_dir, '.plugin-cache.yaml'), data)

    def set_config(self, config: ChangelogConfig):
        config_dir = self.paths.changelog_dir
        os.makedirs(config_dir, exist_ok=True)
        self.created_dirs.add(config_dir)
        self.config = config
        self.config.store()
        self._written(self.paths.config_path)

    def add_fragment(self, fragment_name: str, content: str):
        fragment_dir = os.path.join(self.paths.changelog_dir, self.config.notes_dir)
        os.makedirs(fragment_dir, exist_ok=True)
        self.created_dirs.add(self.paths.changelog_dir)
        self.created_dirs.add(fragment_dir)
        self._write(os.path.join(fragment_dir, fragment_name), content.encode('utf-8'))

    def add_fragment_line(self, fragment_name: str, section: str, lines: Union[List[str], str]):
        self.add_fragment(fragment_name, yaml.dump({section: lines}, Dumper=yaml.SafeDumper))

    def _plugin_base(self, plugin_type):
        if plugin_type == 'module':
            return ['plugins', 'modules']
        return ['plugins', plugin_type]

    def add_plugin(self, plugin_type: str, name: str, content: str, subdirs: List[str] = None):
        plugin_dir = self.paths.base_dir
        for part in self._plugin_base(plugin_type) + (subdirs or []):
            plugin_dir = os.path.join(plugin_dir, part)
            os.makedirs(plugin_dir, exist_ok=True)
            self.created_dirs.add(plugin_dir)
        self._write(os.path.join(plugin_dir, name), content.encode('utf-8'))

    def run_tool(self, command: str, arguments: List[str], cwd: Optional[str] = None) -> int:
        old_cwd = os.getcwd()
        if cwd is not None:
            cwd = os.path.join(self.paths.base_dir, cwd)
        else:
            cwd = self.paths.base_dir
        os.chdir(cwd)
        try:
            return run_changelog_tool(['changelog', command] + arguments)
        finally:
            os.chdir(old_cwd)

    def diff(self) -> Differences:
        result = Differences()
        existing_dirs = set()
        existing_files = set()
        for dirpath, _, filenames in os.walk(self.paths.base_dir):
            reldir = os.path.relpath(dirpath, self.paths.base_dir)
            if reldir != '.':
                existing_dirs.add(dirpath)
                if dirpath not in self.created_dirs:
                    result.added_dirs.append(reldir)
            for filename in filenames:
                real_path = os.path.join(dirpath, filename)
                existing_files.add(real_path)
                with open(real_path, 'rb') as f:
                    data = f.read()
                path = os.path.normpath(os.path.join(reldir, filename))
                result.file_contents[path] = data
                if real_path in self.created_files:
                    if data != self.created_files[real_path]:
                        result.changed_files.append(path)
                        result.file_differences[path] = (self.created_files[real_path], data)
                else:
                    result.added_files.append(path)
        for path in self.created_dirs:
            if path not in existing_dirs:
                rel = os.path.relpath(path, self.paths.base_dir)
                result.removed_dirs.append(rel)
        for path in self.created_files:
            if path not in existing_files:
                rel = os.path.relpath(path, self.paths.base_dir)
                result.removed_files.append(rel)
        result.sort()
        return result


class AnsibleChangelogEnvironment(ChangelogEnvironment):
    def __init__(self, base_path: pathlib.Path):
        super().__init__(base_path, PathsConfig.force_ansible(base_dir=str(base_path)), is_collection=False)

    def _plugin_base(self, plugin_type):
        if plugin_type == 'module':
            return ['lib', 'ansible', 'modules']
        return ['lib', 'ansible', 'plugins', plugin_type]


class CollectionChangelogEnvironment(ChangelogEnvironment):
    namespace: str
    collection: str
    collection_name: str

    def __init__(self, base_path: pathlib.Path, namespace: str, collection: str):
        collection_path = base_path / 'ansible_collections' / namespace / collection
        collection_path.mkdir(parents=True, exist_ok=True)
        super().__init__(base_path, PathsConfig.force_collection(base_dir=str(collection_path)), is_collection=True)
        self.namespace = namespace
        self.collection = collection
        self.collection_name = '{0}.{1}'.format(namespace, collection)

    def set_galaxy(self, data: Any):
        data = dict(data)
        if 'namespace' not in data:
            data['namespace'] = self.namespace
        if 'name' not in data:
            data['name'] = self.collection
        galaxy_path = os.path.join(self.paths.base_dir, 'galaxy.yml')
        self._write_yaml(galaxy_path, data)
        self.paths.galaxy_path = galaxy_path


@pytest.fixture
def ansible_changelog(tmp_path_factory) -> AnsibleChangelogEnvironment:
    return AnsibleChangelogEnvironment(tmp_path_factory.mktemp('changelog-test'))


@pytest.fixture
def collection_changelog(tmp_path_factory, namespace: str = 'acme', collection: str = 'test') -> CollectionChangelogEnvironment:
    base_path = tmp_path_factory.mktemp('changelog-test')
    collection_path_env = 'ANSIBLE_COLLECTIONS_PATHS'
    original_path = os.environ.get(collection_path_env)
    os.environ[collection_path_env] = str(base_path)
    yield CollectionChangelogEnvironment(base_path, namespace, collection)
    if original_path is None:
        del os.environ[collection_path_env]
    else:
        os.environ[collection_path_env] = original_path


def create_plugin(**parts):
    result = [
        '#!/usr/bin/python',
        '# Copyright 2020 Ansible',
        '# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)',
        '',
        'from __future__ import absolute_import, division, print_function',
        '__metaclass__ = type',
    ]

    for part, data in parts.items():
        if not isinstance(data, str):
            data = yaml.dump(data, Dumper=yaml.SafeDumper)
        result.extend(['', '{part} = {data!r}'.format(part=part, data=data)])

    return '\n'.join(result)
