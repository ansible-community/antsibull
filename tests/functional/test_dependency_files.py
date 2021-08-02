from packaging.version import Version as PypiVer
from semantic_version import Version as SemVer

import pytest

from antsibull.dependency_files import BuildFile


SIMPLE_TEST_FILE = """_ansible_version: 4
_ansible_base_version: 2.11.0rc1
community.general: >=1.0.0,<2.0.0
community.routeros: >=2.0.0-a2,<3.0.0
"""

SIMPLE_TEST_DEPS = {'community.general': SemVer('1.0.0'),
                    'community.routeros': SemVer('2.0.0-a2'),
                    }

@pytest.mark.parametrize('dependencies, file_contents', ((SIMPLE_TEST_DEPS, SIMPLE_TEST_FILE),))
def test_build_file_write(tmpdir, dependencies, file_contents):
    filename = tmpdir / 'test.build'
    bf = BuildFile(filename)
    bf.write(PypiVer('4.0.0'), '2.11.0rc1', dependencies)

    with open(filename) as f:
        assert f.read() == file_contents
