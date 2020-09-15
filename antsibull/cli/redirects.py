#!/usr/bin/python3 -tt
import os.path
import tempfile

from antsibull.docs_parsing.plugindump import get_redirected_plugin_dump
from antsibull.venv import VenvRunner

# https://docs.ansible.com/ansible/{$VERSION,latest,devel}/
URL_PREFIX = '^(/ansible/[^/]+)/'
# /var/www/html/ansible/prod/
FS_PREFIX = '/srv/ansible/tmp'


def old_to_new_redirect(plugin_type, old, new):
    """
    Format a redirect for placement in the 2.10+ tree.

    This will create a redirect string from a 2.9 or less location to the 2.10 and newer location.

    :arg plugin_type: The type of the plugin.
    :old_name: The old name is the short name that was usable in past ansible releases.
    :new_name: The new name is a FQCN.
    """

    namespace, collection, new_name = new.split('.', 2)

    if plugin_type == 'module':
        old_url = f'{URL_PREFIX}modules/{old}_module.html'
    else:
        old_url = f'{URL_PREFIX}plugins/{plugin_type}/{old}.html'

    # Make the Redirect temporary until we're done testing it.
    # return (f'RedirectMatch permanent "{old_url}"'
    return (f'RedirectMatch "{old_url}"'
            f' "$1/collections/{namespace}/{collection}/{new_name}_{plugin_type}.html"')


def new_to_old_redirect(plugin_type, old, new):
    """
    Format a redirect for placement in the 2.9 or less tree.

    This will create a redirect string from a 2.10 or greater location to the 2.9 or less location.

    :arg plugin_type: The type of the plugin.
    :old_name: The old name is the short name that was usable in past ansible releases.
    :new_name: The new name is a FQCN.
    """
    namespace, collection, new_name = new.split('.', 2)

    if plugin_type == 'module':
        old_url = f'$1/modules/{old}_module.html'
    else:
        old_url = f'$1/plugins/{plugin_type}/{old}.html'

    # Make the Redirect temporary until we're done testing it.
    # return (f'RedirectMatch permanent'
    return (f'RedirectMatch'
            f' "{URL_PREFIX}collections/{namespace}/{collection}/{new_name}_{plugin_type}.html"'
            f' "{old_url}"')


def write_apache_file(redirects, directory):
    """
    Write the apache config to disk.

    :arg redirects: The redirect lines to put into the new config file
    :arg directory: The directory teh apache config file will land in

    .. warn:: This writes an apache .htaccess file which overwrites any existing one.
    """
    apache_file = os.path.join(FS_PREFIX, directory, '.htaccess')
    with open(apache_file, 'w') as f:
        f.write('\n'.join(redirects))


def run(new_dirs, old_dirs):
    with tempfile.TemporaryDirectory() as tmp_dir:
        venv = VenvRunner('ansible-venv', tmp_dir)
        ansible_installed_dir = venv._python('-c', 'import sysconfig; print(sysconfig.get_path("purelib"))')
        ansible_installed_dir = ansible_installed_dir.stdout.decode('utf-8').strip()

        # FIXME: Use the latest ansible or from a command line switch
        venv.install_package('ansible==2.10.0a9')

        # FIXME: This function saves global state (using python's import mechanisms) so once we have
        # multiple ansible-base's (one for 2.10, one for 2.11, one for devel, etc), then we'll need
        # to modify this script to run multiple times.  It won't be able to handle multiple
        # ansible-base's from a single run.
        plugin_data = get_redirected_plugin_dump(ansible_installed_dir)

        redirects_for_new_site = []
        redirects_for_old_site = []
        # FIXME: Take care of renames inside of collections as well
        # for collection_name in sorted(plugin_data):
        plugins = plugin_data['ansible.builtin']
        for plugin_type, plugin_list in sorted(plugins.items()):
            redirects = plugins[plugin_type]
            for old, new in sorted(redirects.items()):
                # The plugin has not moved
                if not new:
                    new = f'ansible.builtin.{old}'

                redirects_for_new_site.append(old_to_new_redirect(plugin_type, old, new))
                redirects_for_old_site.append(new_to_old_redirect(plugin_type, old, new))

        for directory in old_dirs:
            # Redirects when people use the version switcher to go from 2.10+ to the 2.8 and 2.9
            # docs.
            write_apache_file(redirects_for_old_site, directory)

        for directory in new_dirs:
            # Redirects when people use the version switcher to go from 2.8 or 2.9 to 2.10+
            write_apache_file(redirects_for_new_site, directory)


def main():
    # FIXME: How to handle devel and latest?  They don't have real directories for the .htaccess
    # to land in.  Since this is a regex, they may just work.

    # FIXME: Add devel and 2.8 to this
    run(new_dirs=['2.10'], old_dirs=['2.9'])


if __name__ == '__main__':
    main()
