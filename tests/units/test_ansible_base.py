from packaging.version import  Version
import pytest

import antsibull.ansible_base as ab


@pytest.mark. parametrize('version', ('2.9', '2.9.10', '1.0', '1', '0.7', '2.10', '2.10.0',
                                      '2.10.8', '2.10.12'))
def test_get_core_package_name_returns_ansible_base(version):
    assert ab.get_ansible_core_package_name(version) == 'ansible-base'
    assert ab.get_ansible_core_package_name(Version(version)) == 'ansible-base'


@pytest.mark.parametrize('version', ('2.11', '2.11.0', '2.11.8', '2.11.12', '2.13',
                                     '2.11.0a1', '3', '3.7.10'))
def test_get_core_package_name_returns_ansible_core(version):
    assert ab.get_ansible_core_package_name(version) == 'ansible-core'
    assert ab.get_ansible_core_package_name(Version(version)) == 'ansible-core'
