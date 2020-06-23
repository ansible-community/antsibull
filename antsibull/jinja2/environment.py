# Copyright: (c) 2019-2020 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


import json
import os.path

from jinja2 import Environment, FileSystemLoader, PackageLoader

from .filters import do_max, documented_type, html_ify, rst_ify, rst_fmt, rst_xline
from .tests import still_relevant, test_list


# kludge_ns gives us a kludgey way to set variables inside of loops that need to be visible outside
# the loop.  We can get rid of this when we no longer need to build docs with less than Jinja-2.10
# http://jinja.pocoo.org/docs/2.10/templates/#assignments
# With Jinja-2.10 we can use jinja2's namespace feature, restoring the namespace template portion
# of: fa5c0282a4816c4dd48e80b983ffc1e14506a1f5
NS_MAP = {}


def to_kludge_ns(key, value):
    NS_MAP[key] = value
    return ""


def from_kludge_ns(key):
    return NS_MAP[key]


def doc_environment(template_location):
    if isinstance(template_location, str) and os.path.exists(template_location):
        loader = FileSystemLoader(template_location)
    else:
        if isinstance(template_location, str):
            template_pkg = template_location
            template_path = 'templates'
        else:
            template_pkg = template_location[0]
            template_path = template_location[1]

        loader = PackageLoader(template_pkg, template_path)

    env = Environment(loader=loader,
                      variable_start_string="@{",
                      variable_end_string="}@",
                      trim_blocks=True)
    env.globals['xline'] = rst_xline

    # Can be removed (and template switched to use namespace) when we no longer need to build
    # with <Jinja-2.10
    env.globals['to_kludge_ns'] = to_kludge_ns
    env.globals['from_kludge_ns'] = from_kludge_ns
    if 'max' not in env.filters:
        # Jinja < 2.10
        env.filters['max'] = do_max

    if 'tojson' not in env.filters:
        # Jinja < 2.9
        env.filters['tojson'] = json.dumps

    env.filters['rst_ify'] = rst_ify
    env.filters['html_ify'] = html_ify
    env.filters['fmt'] = rst_fmt
    env.filters['xline'] = rst_xline
    env.filters['documented_type'] = documented_type
    env.tests['list'] = test_list
    env.tests['still_relevant'] = still_relevant

    return env
