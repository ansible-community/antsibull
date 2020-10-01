# Copyright: (c) 2014, James Tanner <tanner.jc@gmail.com>
# Copyright: (c) 2018, Ansible Project
# Copyright: (c) 2020, Felix Fontein
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Parts taken from Ansible's ansible-doc sources

import argparse
import json
import sys

import ansible.plugins.loader as plugin_loader

from ansible import constants as C
from ansible import release as ansible_release
from ansible.cli import doc
from ansible.cli.arguments import option_helpers as opt_help
from ansible.collections.list import list_collection_dirs
from ansible.galaxy.collection import CollectionRequirement
from ansible.module_utils._text import to_native
from ansible.plugins.loader import fragment_loader
from ansible.utils.collection_loader import AnsibleCollectionConfig
from ansible.utils.plugin_docs import get_docstring


def load_all_plugins(plugin_type, basedir, coll_filter):
    loader = getattr(plugin_loader, '%s_loader' % plugin_type)

    if basedir:
        loader.add_directory(basedir, with_subdir=True)

    loader._paths = None  # reset so we can use subdirs below

    plugin_list = set()

    if coll_filter is None:
        paths = loader._get_paths_with_context()
        for path_context in paths:
            plugin_list.update(doc.DocCLI.find_plugins(path_context.path, path_context.internal, plugin_type))

    doc.add_collection_plugins(plugin_list, plugin_type, coll_filter=coll_filter)

    result = {}
    for plugin in plugin_list:
        result[plugin] = {}
        try:
            plugin_context = loader.find_plugin_with_context(plugin, mod_type='.py', ignore_deprecated=True, check_aliases=True)
            if not plugin_context.resolved:
                result[plugin]['error'] = 'Cannot find plugin'
                continue
            plugin_name = plugin_context.plugin_resolved_name
            filename = plugin_context.plugin_resolved_path
            collection_name = plugin_context.plugin_resolved_collection

            result[plugin].update({
                'plugin_name': plugin_name,
                'filename': filename,
                'collection_name': collection_name,
            })

            documentation, plainexamples, returndocs, metadata = get_docstring(
                filename, fragment_loader, verbose=False,
                collection_name=collection_name, is_module=(plugin_type == 'module'))

            if documentation is None:
                result[plugin]['error'] = 'No valid documentation found'
                continue

            documentation['filename'] = filename
            documentation['collection'] = collection_name

            ansible_doc = {
                'doc': documentation,
                'examples': plainexamples,
                'return': returndocs,
                'metadata': metadata,
            }

            try:
                json.dumps(ansible_doc)
                result[plugin]['ansible-doc'] = ansible_doc
            except Exception as e:
                result[plugin]['error'] = 'Cannot serialize documentation as JSON: %s' % to_native(e)
        except Exception as e:
            result[plugin]['error'] = 'Missing documentation or could not parse documentation: %s' % to_native(e)

    return result


def main(args):
    parser = argparse.ArgumentParser(prog=args[0], description='Bulk extraction of Ansible plugin docs.')
    parser.add_argument('args', nargs='?', help='Collection filter', metavar='collection_filter')
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

    # Export collection data
    b_colldirs = list_collection_dirs(coll_filter=coll_filter)
    for b_path in b_colldirs:
        collection = CollectionRequirement.from_path(b_path, False, fallback_metadata=True)

        result['collections']['{0}.{1}'.format(collection.namespace, collection.name)] = {
            'path': to_native(b_path),
            'version': collection.metadata.version if collection.metadata.version != '*' else None,
        }

    if arguments.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))


if __name__ == '__main__':
    main(sys.argv)
