# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

"""
Persist collection infornation used to build Ansible.

Build dependency files list the dependencies of an Ansible release along with the versions that are
compatible with that release.

When we initially build an Ansible major release, we'll use certain versions of collections.  We
don't want to install backwards incompatible collections until the next major Ansible release.
"""

from typing import TYPE_CHECKING, Dict, List, Mapping, NamedTuple, Optional

if TYPE_CHECKING:
    from packaging.version import Version as PypiVer
    from semantic_version import Version as SemVer


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
    ansible_version: Optional[str] = None

    for line in parse_pieces_file(filename):
        record = [entry.strip() for entry in line.split(':', 1)]

        if record[0] in ('_ansible_version', '_acd_version'):
            if ansible_version is not None:
                raise InvalidFileFormat(f'{filename} specified _ansible_version/_acd_version'
                                        ' more than once')
            ansible_version = record[1]
            continue

        if record[0] == '_ansible_base_version':
            if ansible_base_version is not None:
                raise InvalidFileFormat(f'{filename} specified _ansible_base_version'
                                        ' more' ' than once')
            ansible_base_version = record[1]
            continue

        deps[record[0]] = record[1]

    if ansible_base_version is None:
        raise InvalidFileFormat(f'{filename} was invalid.  It did not contain'
                                ' the required ansible_base_version field')
    if ansible_version is None:
        raise InvalidFileFormat(f'{filename} was invalid.  It did not contain'
                                ' the required ansible_version field')

    return DependencyFileData(ansible_version, ansible_base_version, deps)


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

    def write(self, ansible_version: str, ansible_base_version: str,
              included_versions: Mapping[str, str]) -> None:
        """
        Write a list of all the dependent collections included in this Ansible release.

        :arg ansible_version: The version of Ansible that is being recorded.
        :arg ansible_base_version: The version of Ansible base that will be depended on.
        :arg included_versions: Dictionary mapping collection names to the version range in this
            version of Ansible.
        """
        records = []
        for dep, version in included_versions.items():
            records.append(f'{dep}: {version}')
        records.sort()

        with open(self.filename, 'w') as f:
            f.write(f'_ansible_version: {ansible_version}\n')
            f.write(f'_ansible_base_version: {ansible_base_version}\n')
            f.write('\n'.join(records))
            f.write('\n')


class BuildFile:
    def __init__(self, build_file: str) -> None:
        self.filename: str = build_file

    def parse(self) -> DependencyFileData:
        """Parse the build from a dependency file."""
        return _parse_name_version_spec_file(self.filename)

    def write(self, ansible_version: 'PypiVer', ansible_base_version: str,
              dependencies: Mapping[str, 'SemVer']) -> None:
        """
        Write a build dependency file.

        A build dependency file records the collections that went into a given Ansible release along
        with the range of versions that are allowed for that collection.  The range is meant to
        define the set of collection versions that are compatible with what was present in the
        collection as of the first beta release, when we feature freeze the collections.

        :arg ansible_version: The version of Ansible that is being recorded.
        :arg ansible_base_version: The version of Ansible base that will be depended on.
        :arg dependencies: Dictionary with keys of collection names and values of the latest
            versions of those collections.
        """
        records = []
        for dep, version in dependencies.items():
            records.append(f'{dep}: >={version.major}.{version.minor}.0,<{version.next_major()}')
        records.sort()

        with open(self.filename, 'w') as f:
            if ansible_version.major > 2:
                # Ansible 3.0.0 and newer use semver, so we only need the major version
                f.write(f'_ansible_version: {ansible_version.major}\n')
            else:
                f.write(f'_ansible_version: {ansible_version.major}.{ansible_version.minor}\n')
            f.write(f'_ansible_base_version: {ansible_base_version}\n')
            f.write('\n'.join(records))
            f.write('\n')
