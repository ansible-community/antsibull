# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Persist collection infornation used to build Ansible.

Build dependency files list the dependencies of an ACD release along with the
versions that are compatible with that release.

When we initially build an ACD major release, we'll use certain versions of collections.
We don't want to install backwards incompatible collections until the next major ACD release.
"""

from typing import TYPE_CHECKING, Dict, List, Mapping, NamedTuple, Optional

if TYPE_CHECKING:
    from packaging.version import Version as PyPiVersion
    from semantic_version import Version as SemVersion


class DependencyFileData(NamedTuple):
    ansible_version: str
    ansible_base_version: str
    deps: Dict[str, str]


class InvalidFileFormat(Exception):
    pass


def parse_pieces_file(pieces_file: str) -> List[str]:
    with open(pieces_file, 'rb') as f:
        contents = f.read()

    contents = contents.decode('utf-8')
    # One collection per line, ignoring comments and empty lines
    # TODO: PY3.8:
    # collections = [c for line in contents.split('\n')
    #                if (c := line.strip()) and not c.startswith('#')]
    collections = [line.strip() for line in contents.split('\n')
                   if line.strip() and not line.strip().startswith('#')]
    return collections


def _parse_name_version_spec_file(filename: str) -> DependencyFileData:
    deps: Dict[str, str] = {}
    ansible_base_version: Optional[str] = None
    acd_version: Optional[str] = None

    with open(filename, 'r') as f:
        for line in f:
            record = [entry.strip() for entry in line.split(':', 1)]

            if record[0] == '_acd_version':
                if acd_version is not None:
                    raise InvalidFileFormat(f'{filename} specified _acd_version'
                                            ' more than once')
                acd_version = record[1]
                continue

            if record[0] == '_ansible_base_version':
                if ansible_base_version is not None:
                    raise InvalidFileFormat(f'{filename} specified _ansible_base_version'
                                            ' more' ' than once')
                ansible_base_version = record[1]
                continue

            deps[record[0]] = record[1]

    if ansible_base_version is None or acd_version is None:
        raise InvalidFileFormat(f'{filename} was invalid.  It did not contain'
                                ' required fields')

    return DependencyFileData(acd_version, ansible_base_version, deps)


class DepsFile:
    """
    File containing the collections which are part of an Ansible release.

    A DepsFile contains a sequence of lines with a collection name, ": ", and then an exact
    version of the collection.  It tracks the exact collection-versions which were installed
    with a particular ansible version.

    The deps file has two special lines which are not collections.  They are::

        _ansible_version: X1.Y1.Z1
        _ansible_base_version: X2.Y2.Z2

    These are, respectively, the ansible version that was built and the ansible-base version which
    it was built against.  Note that the ansible release will depend on a compatible version of that
    ansible base version, not an exact dependency on that precise version.
    """

    def __init__(self, deps_file: str) -> None:
        """
        Create a :mod:`DepsFile`.

        :arg deps_file: filename of the `DepsFile`.
        """
        self.filename: str = deps_file

    def parse(self) -> DependencyFileData:
        """Parse the deps from a dependency file."""
        return _parse_name_version_spec_file(self.filename)

    def write(self, acd_version: str, ansible_base_version: str,
              included_versions: Mapping[str, str]) -> None:
        """
        Write a list of all the dependent collections included in this ACD release.

        :arg acd_version: The version of Ansible that is being recorded.
        :arg ansible_base_version: The version of Ansible base that will be depended on.
        :arg included_versions: Dictionary mapping collection names to the version range in this
            version of Ansible.
        """
        records = []
        for dep, version in included_versions.items():
            records.append(f'{dep}: {version}')
        records.sort()

        with open(self.filename, 'w') as f:
            f.write(f'_acd_version: {acd_version}\n')
            f.write(f'_ansible_base_version: {ansible_base_version}\n')
            f.write('\n'.join(records))
            f.write('\n')


class BuildFile:
    def __init__(self, build_file: str) -> None:
        self.filename: str = build_file

    def parse(self) -> DependencyFileData:
        """Parse the build from a dependency file."""
        return _parse_name_version_spec_file(self.filename)

    def write(self, acd_version: 'PyPiVersion', ansible_base_version: str,
              dependencies: Mapping[str, 'SemVersion']) -> None:
        """
        Write a build dependency file.

        A build dependency file records the collections that went into a given Ansible release along
        with the exact version of the collection that was included.

        :arg acd_version: The version of Ansible that is being recorded.
        :arg ansible_base_version: The version of Ansible base that will be depended on.
        :arg dependencies: Dictionary with keys of collection names and values of versions.
        """
        records = []
        for dep, version in dependencies.items():
            records.append(f'{dep}: >={version.major}.0.0,<{version.next_major()}')
        records.sort()

        with open(self.filename, 'w') as f:
            f.write(f'_acd_version: {acd_version.major}.{acd_version.minor}\n')
            f.write(f'_ansible_base_version: {ansible_base_version}\n')
            f.write('\n'.join(records))
            f.write('\n')
