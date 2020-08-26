# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020

import json
import os.path
import tempfile

import sh
from jinja2 import Template

from . import app_context
from .dependency_files import DepsFile
from .utils.get_pkg_data import get_antsibull_data


def build_collection_command():
    app_ctx = app_context.app_ctx.get()
    with tempfile.TemporaryDirectory() as working_dir:
        collection_dir = os.path.join(working_dir, 'community', 'ansible')

        sh.ansible_galaxy('collection', 'init', 'community.ansible', '--init-path', working_dir)
        # Copy the README.md file
        readme = get_antsibull_data('README_md.txt')
        with open(os.path.join(collection_dir, 'README.md'), 'wb') as f:
            f.write(readme)

        # Parse the deps file
        deps_file = DepsFile(os.path.join(app_ctx.extra['data_dir'], app_ctx.extra['deps_file']))
        dummy1_, dummy2_, deps = deps_file.parse()

        # Template the galaxy.yml file
        dep_string = json.dumps(deps)
        dep_string.replace(', ', ',\n    ')
        galaxy_yml = get_antsibull_data('galaxy_yml.j2').decode('utf-8')
        galaxy_yml_tmpl = Template(galaxy_yml)
        galaxy_yml_contents = galaxy_yml_tmpl.render(version=app_ctx.extra['ansible_version'],
                                                     dependencies=dep_string)

        with open(os.path.join(collection_dir, 'galaxy.yml'), 'w') as f:
            f.write(galaxy_yml_contents)

        sh.ansible_galaxy('collection', 'build',
                          '--output-path', app_ctx.extra['collection_dir'],
                          collection_dir)

    return 0
