from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import operator as py_operator

from packaging.version import parse


def packaging_version(version_a, version_b, op):
    a = parse(version_a)
    b = parse(version_b)
    method = getattr(py_operator, {
        '<': 'lt',
        '<=': 'le',
        '==': 'eq',
        '>=': 'ge',
        '>': 'gt',
    }[op])
    return method(a, b)


class TestModule:
    ''' Version jinja2 tests '''

    def tests(self):
        return {
            '_antsibull_packaging_version': packaging_version,
        }
