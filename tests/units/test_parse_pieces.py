import pytest

from antsibull import dependency_files as df

PIECES = """
community.general
# This is a comment
community.aws
    # Supported by ansible
    ansible.posix
    ansible.windows
# Third parties
purestorage.flasharray
"""

PARSED_PIECES = ['community.general', 'community.aws', 'ansible.posix', 'ansible.windows', 'purestorage.flasharray']

DEPS = """
_ansible_version: 2.10.5
# this is a comment
_ansible_base_version: 2.10.4
    # supported by ansible
    ansible.netcommon: 1.4.1
    ansible.posix: 1.1.1
    ansible.windows: 1.3.0
# third parties
dellemc.os10: 1.0.2
"""

PARSED_DEPS_ANSIBLE_VERSION = '2.10.5'
PARSED_DEPS_ANSIBLE_BASE_VERSION = '2.10.4'
PARSED_DEPS_DEPS = {
    'ansible.netcommon': '1.4.1',
    'ansible.posix': '1.1.1',
    'ansible.windows': '1.3.0',
    'dellemc.os10': '1.0.2'
}

BUILD = """
_ansible_version: 2.10
# this is a comment
_ansible_base_version: 2.10.1
    # supported by ansible
    ansible.netcommon: >=1.2.0,<2.0.0
    ansible.posix: >=1.1.0,<2.0.0
    ansible.windows: >=1.0.0,<2.0.0
# third parties
dellemc.os10: >=1.0.0,<1.1.0
"""

PARSED_BUILD_ANSIBLE_VERSION = '2.10'
PARSED_BUILD_ANSIBLE_BASE_VERSION = '2.10.1'
PARSED_BUILD_DEPS = {
    'ansible.netcommon': '>=1.2.0,<2.0.0',
    'ansible.posix': '>=1.1.0,<2.0.0',
    'ansible.windows': '>=1.0.0,<2.0.0',
    'dellemc.os10': '>=1.0.0,<1.1.0'
}

def test_parse_pieces(tmp_path):
    pieces_filename = tmp_path / 'pieces.in'
    with open(pieces_filename, 'w') as f:
        f.write(PIECES)
    assert df.parse_pieces_file(pieces_filename) == PARSED_PIECES

def test_deps_file_parse(tmp_path):
    deps_filename = tmp_path / 'deps.in'
    with open(deps_filename, 'w') as f:
        f.write(DEPS)
    parsed_deps = df.DepsFile(deps_filename).parse()
    assert parsed_deps.ansible_version == PARSED_DEPS_ANSIBLE_VERSION
    assert parsed_deps.ansible_base_version == PARSED_DEPS_ANSIBLE_BASE_VERSION
    assert parsed_deps.deps == PARSED_DEPS_DEPS

def test_build_file_parse(tmp_path):
    build_filename = tmp_path / 'build.in'
    with open(build_filename, 'w') as f:
        f.write(BUILD)
    parsed_build = df.DepsFile(build_filename).parse()
    assert parsed_build.ansible_version == PARSED_BUILD_ANSIBLE_VERSION
    assert parsed_build.ansible_base_version == PARSED_BUILD_ANSIBLE_BASE_VERSION
    assert parsed_build.deps == PARSED_BUILD_DEPS
