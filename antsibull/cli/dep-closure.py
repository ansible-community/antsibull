#!/usr/bin/python3 -tt

import json
import pathlib
import sys

from collections import namedtuple

from semantic_version import Version as SemVer, SimpleSpec as SemVerSpec


ansible_collection_dir = pathlib.Path(sys.argv[1])

CollectionRecord = namedtuple('CollectionRecord', ('version', 'dependencies'))


def parse_manifest(collection_dir):
    manifest = collection_dir.joinpath('MANIFEST.json')
    with manifest.open() as f:
        manifest_data = json.load(f)['collection_info']

    collection_record = {f'{manifest_data["namespace"]}.{manifest_data["name"]}':
                         CollectionRecord(manifest_data['version'],
                                          manifest_data['dependencies'])
                         }

    return collection_record


def analyze_deps(collections):
    errors = []

    # Look at dependencies
    # make sure their dependencies are found
    for collection_name, collection_info in collections.items():
        for dep_name, dep_version_spec in collection_info.dependencies.items():
            if dep_name not in collections:
                errors.append(f'{collection_name} missing: {dep_name} ({dep_version_spec})')
                continue

            dependency_version = SemVer(collections[dep_name].version)
            if dependency_version not in SemVerSpec(dep_version_spec):
                errors.append(f'{collection_name} version_conflict:'
                              f' {dep_name}-{str(dependency_version)} but needs'
                              f' {dep_version_spec}')
                continue

    return errors


def main():
    collections = {}
    for namespace_dir in (n for n in ansible_collection_dir.iterdir() if n.is_dir()):
        for collection_dir in (c for c in namespace_dir.iterdir() if c.is_dir()):
            try:
                collections.update(parse_manifest(collection_dir))
            except FileNotFoundError:
                print(f'{collection_dir} is not a valid collection')

    errors = analyze_deps(collections)
    if errors:
        print('== Dependency errors detected ==')
        print('\n* ', end='')
        print('\n* '.join(errors))
        sys.exit(1)
    else:
        print('== All dependencies were satisfied ==')

    sys.exit(0)

if __name__ == '__main__':
    main()
