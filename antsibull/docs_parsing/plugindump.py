# Copyright: 2020, Ansible Project
# Author: Matt Davis, nitzmahone
# License: GPLv3+

import importlib
import os
import pkgutil
import sys
from pathlib import Path

from ..constants import DOCUMENTABLE_PLUGINS
from ..logging import log


# note these are the loader attribute prefix names from loader.py, we convert them later to the collection loader plugin type values
#PLUGIN_TYPES = ['module', 'become', 'cache', 'callback', 'connection', 'lookup', 'shell', 'inventory']

mlog = log.fields(mod=__name__)


def get_collection_names(site_dir):
    pkg_root = Path(site_dir, 'ansible_collections')
    namespaces = [p[1] for p in pkgutil.iter_modules([pkg_root]) if p[2]]

    collections = []

    for ns in namespaces:
        collections += [p[1] for p in pkgutil.iter_modules([Path(pkg_root, ns)], f'{ns}.') if p[2]]

    # hardcode the builtin collection as well
    collections.append('ansible.builtin')

    return collections


def get_builtin_plugins(loader):
    return [Path(p).stem for p in loader.all(path_only=True)]


def get_collection_plugins(plugin_type, collection_name, loader):
    if collection_name == 'ansible.builtin':
        return get_builtin_plugins(loader)

    plugins = []

    try:
        plugin_pkg = importlib.import_module(f'ansible_collections.{collection_name}.plugins.{plugin_type}')
    except ImportError:
        return plugins

    # ignore packages, only include modules
    plugins = [p[1] for p in pkgutil.walk_packages(plugin_pkg.__path__, f'') if not p[2]]

    return plugins


def get_redirected_plugin_dump(ansible_base_site_dir, acd_site_dir=None):
    flog = mlog.fields(func='get_redirected_plugin_dump')
    flog.debug('Enter')

    if not acd_site_dir:
        acd_site_dir = ansible_base_site_dir

    if not Path(ansible_base_site_dir).is_dir() or not Path(ansible_base_site_dir, 'ansible').is_dir():
        raise FileNotFoundError(f'`ansible` package not found at {ansible_base_site_dir}')

    if not Path(acd_site_dir).is_dir() or not Path(acd_site_dir, 'ansible_collections').is_dir():
        raise FileNotFoundError(f'ansible_collections` package not found at {acd_site_dir}')

    if ansible_base_site_dir in sys.path:
        sys.path.remove(ansible_base_site_dir)

    sys.path[0] = ansible_base_site_dir

    os.environ['ANSIBLE_DEPRECATION_WARNINGS'] = '0'
    os.environ['ANSIBLE_COLLECTIONS_PATH'] = acd_site_dir
    os.environ['ANSIBLE_COLLECTIONS_SCAN_SYS_PATH'] = '0'

    from ansible.errors import AnsiblePluginRemovedError
    from ansible.plugins import loader as core_loader
    from ansible.utils.collection_loader import AnsibleCollectionRef

    # get all the collection names we can find in the acd site dir
    collection_names = get_collection_names(acd_site_dir)

    result = dict()

    for collection_name in collection_names:
        collection_map = dict()
        result[collection_name] = collection_map
        collection_pkg = importlib.import_module(f'ansible_collections.{collection_name}')

        for plugin_type in DOCUMENTABLE_PLUGINS:
            plugin_map = dict()
            collection_map[plugin_type] = plugin_map
            loader = getattr(core_loader, plugin_type + '_loader')

            plugin_type_subdir = AnsibleCollectionRef.legacy_plugin_dir_to_plugin_type(loader.subdir)
            plugin_map.update({k: '' for k in get_collection_plugins(plugin_type_subdir, collection_name, loader)})

            # grab the pre-chewed collection metadata the loader stuffed in
            collection_meta = collection_pkg._collection_meta

            plugin_type_meta = collection_meta.get('plugin_routing', {}).get(plugin_type_subdir, {})
            for plugin_name, routing_entry in plugin_type_meta.items():
                redirect = routing_entry.get('redirect')
                if not redirect:
                    continue

                try:
                    ctx = loader.find_plugin_with_context(redirect)
                except AnsiblePluginRemovedError:
                    flog.warning('{plugin_type} {plugin_name} marked as removed',
                                 plugin_type=plugin_type, plugin_name=plugin_name)
                    continue

                if ctx.resolved:
                    plugin_map[plugin_name] = ctx.redirect_list[-1]
                else:
                    flog.warning('redirected {plugin_type} {plugin_name} from collection'
                                 ' {collection_name} did not resolve',
                                 plugin_type=plugin_type, plugin_name=plugin_name,
                                 collection_name=collection_name)

    flog.debug('Exit')
    return result


def main():
    if len(sys.argv) != 2:
        print('usage: plugindump [ansible_base_site_dir]')
        sys.exit(1)

    dump = get_redirected_plugin_dump(sys.argv[1])

    #print(dump)
    #sys.exit(1)
    for collection_name in sorted(dump):
        plugins = dump[collection_name]
        print(f'collection: {collection_name}')
        for plugin_type in sorted(plugins):
            redirects = plugins[plugin_type]
            print(f'\tplugin type: {plugin_type}')
            for src in sorted(redirects):
                dest = redirects[src]
                print(f'\t\t{src} -> {dest}')


if __name__ == '__main__':
    main()
