# Copyright: (c) 2014, James Tanner <tanner.jc@gmail.com>
# Copyright: (c) 2018, Ansible Project
# Copyright: (c) 2020, Felix Fontein
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Enumerate collections and all their plugin's docs."""

# pylint:disable=protected-access

# Parts taken from Ansible's ansible-doc sources

import argparse
import json
import os
import sys

import yaml

import ansible.plugins.loader as plugin_loader  # pylint:disable=import-error

from ansible import constants as C  # pylint:disable=import-error
from ansible import release as ansible_release  # pylint:disable=import-error
from ansible.cli import doc  # pylint:disable=import-error
from ansible.cli.arguments import option_helpers as opt_help  # pylint:disable=import-error
from ansible.collections.list import list_collection_dirs  # pylint:disable=import-error
from ansible.module_utils._text import to_native  # pylint:disable=import-error
from ansible.module_utils.common.json import AnsibleJSONEncoder  # pylint:disable=import-error
from ansible.plugins.loader import action_loader, fragment_loader  # pylint:disable=import-error
from ansible.utils.collection_loader import AnsibleCollectionConfig  # pylint:disable=import-error
from ansible.utils.plugin_docs import get_docstring  # pylint:disable=import-error


def load_plugin(loader, plugin_type, plugin):
    result = {}
    try:
        plugin_context = loader.find_plugin_with_context(
            plugin, mod_type='.py', ignore_deprecated=True, check_aliases=True)
        if not plugin_context.resolved:
            result['error'] = 'Cannot find plugin'
            return result
        plugin_name = plugin_context.plugin_resolved_name
        filename = plugin_context.plugin_resolved_path
        collection_name = plugin_context.plugin_resolved_collection

        result.update({
            'plugin_name': plugin_name,
            'filename': filename,
            'collection_name': collection_name,
        })

        documentation, plainexamples, returndocs, metadata = get_docstring(
            filename, fragment_loader, verbose=False,
            collection_name=collection_name, is_module=(plugin_type == 'module'))

        if documentation is None:
            result['error'] = 'No valid documentation found'
            return result

        documentation = dict(documentation)

        documentation['filename'] = filename
        documentation['collection'] = collection_name

        if plugin_type == 'module':
            # is there corresponding action plugin?
            if plugin in action_loader:
                documentation['has_action'] = True
            else:
                documentation['has_action'] = False

        ansible_doc = {
            'doc': documentation,
            'examples': plainexamples,
            'return': returndocs,
            'metadata': metadata,
        }

        try:
            # If this fails, the documentation cannot be seralized as JSON
            json.dumps(ansible_doc, cls=AnsibleJSONEncoder)
            # Store result. This is guaranteed to be serializable
            result['ansible-doc'] = ansible_doc
        except Exception as e:  # pylint:disable=broad-except
            result['error'] = (
                f'Cannot serialize documentation as JSON: {to_native(e)}'
            )
    except Exception as e:  # pylint:disable=broad-except
        result['error'] = (
            f'Missing documentation or could not parse documentation: {to_native(e)}'
        )

    return result


def ansible_doc_coll_filter(coll_filter):
    return coll_filter[0] if coll_filter and len(coll_filter) == 1 else None


def match_filter(name, coll_filter):
    if coll_filter is None or name in coll_filter:
        return True
    if '.' not in name and 'ansible.builtin' in coll_filter:
        return True
    for a_filter in coll_filter:
        if name.startswith(f'{a_filter}.'):
            return True
    return False


def load_all_plugins(plugin_type, basedir, coll_filter):
    loader = getattr(plugin_loader, f'{plugin_type}_loader')

    if basedir:
        loader.add_directory(basedir, with_subdir=True)

    loader._paths = None  # reset so we can use subdirs below

    plugin_list = set()

    if match_filter('ansible.builtin', coll_filter):
        paths = loader._get_paths_with_context()
        for path_context in paths:
            plugin_list.update(
                doc.DocCLI.find_plugins(path_context.path, path_context.internal, plugin_type))

    doc.add_collection_plugins(
        plugin_list, plugin_type, coll_filter=ansible_doc_coll_filter(coll_filter))

    result = {}
    for plugin in plugin_list:
        if match_filter(plugin, coll_filter):
            result[plugin] = load_plugin(loader, plugin_type, plugin)

    return result


def load_role(role_mixin, role_name, collection_name, collection_path):
    result = {
        'directory': collection_path,
        'collection_name': collection_name,
    }

    argspec = role_mixin._load_argspec(role_name, collection_path=collection_path)
    _, ansible_doc = role_mixin._build_doc(
        role_name, collection_path, collection_name, argspec, None)

    try:
        # If this fails, the documentation cannot be serialized as JSON
        json.dumps(ansible_doc, cls=AnsibleJSONEncoder)
        # Store result. This is guaranteed to be serializable
        result['ansible-doc'] = ansible_doc
    except Exception as e:  # pylint:disable=broad-except
        result['error'] = (
            f'Cannot serialize documentation as JSON: {to_native(e)}'
        )

    return result


def load_all_roles(RoleMixin, basedir, coll_filter):  # pylint:disable=unused-argument
    role_mixin = RoleMixin()
    roles = role_mixin._find_all_collection_roles()
    result = {}
    for role_name, collection_name, collection_path in roles:
        fqcn = f'{collection_name}.{role_name}'
        if match_filter(fqcn, coll_filter):
            role_data = load_role(role_mixin, role_name, collection_name, collection_path)
            if role_data['ansible-doc'] is None:
                continue
            result[fqcn] = role_data
    return result


def load_collection_meta_manifest(b_manifest_path):
    with open(b_manifest_path, 'rb') as f:
        meta = json.load(f)
    return {
        'namespace': meta['collection_info']['namespace'],
        'name': meta['collection_info']['name'],
        'version': meta['collection_info']['version'],
    }


def load_collection_meta_galaxy(b_galaxy_path):
    with open(b_galaxy_path, 'rb') as f:
        meta = yaml.safe_load(f)
    return {
        'namespace': meta['namespace'],
        'name': meta['name'],
        'version': meta.get('version'),
    }


def load_collection_meta(b_path):
    b_manifest_path = os.path.join(b_path, b'MANIFEST.json')
    b_galaxy_path = os.path.join(b_path, b'galaxy.yml')
    if os.path.exists(b_manifest_path):
        data = load_collection_meta_manifest(b_manifest_path)
    elif os.path.exists(b_galaxy_path):
        data = load_collection_meta_galaxy(b_galaxy_path)
    else:
        # Fallback in case no galaxy.yml is around. This happens for collections
        # checked out from source where galaxy.yml is templated on build.
        data = {
            'version': None,
            'namespace': to_native(os.path.basename(os.path.dirname(b_path))),
            'name': to_native(os.path.basename(b_path)),
        }
    data['path'] = to_native(b_path)
    return data


def main(args):
    parser = argparse.ArgumentParser(
        prog=args[0], description='Bulk extraction of Ansible plugin docs.')
    parser.add_argument('args', nargs='*', help='Collection filter', metavar='collection_filter')
    parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON')
    opt_help.add_basedir_options(parser)

    arguments = parser.parse_args(args[1:])

    basedir = arguments.basedir
    coll_filter = arguments.args or None

    if basedir:
        AnsibleCollectionConfig.playbook_paths = basedir

    result = {
        'plugins': {},
        'collections': {},
    }

    # Export plugin docs
    for plugin_type in C.DOCUMENTABLE_PLUGINS:
        result['plugins'][plugin_type] = load_all_plugins(plugin_type, basedir, coll_filter)

    # Export role docs
    RoleMixin = getattr(doc, 'RoleMixin', None)
    if RoleMixin is not None:
        result['plugins']['role'] = load_all_roles(RoleMixin, basedir, coll_filter)
    else:
        result['plugins']['role'] = {}

    # Export collection data
    b_colldirs = list_collection_dirs(coll_filter=ansible_doc_coll_filter(coll_filter))
    for b_path in b_colldirs:
        meta = load_collection_meta(b_path)
        collection_name = f'{meta["namespace"]}.{meta["name"]}'
        if match_filter(collection_name, coll_filter):
            result['collections'][collection_name] = meta
    if match_filter('ansible.builtin', coll_filter):
        result['collections']['ansible.builtin'] = {
            'path': os.path.dirname(ansible_release.__file__),
            'version': ansible_release.__version__,
        }

    print(json.dumps(
        result, cls=AnsibleJSONEncoder, sort_keys=True, indent=4 if arguments.pretty else None))


if __name__ == '__main__':
    main(sys.argv)
