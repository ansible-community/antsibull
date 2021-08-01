# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2021
"""Entrypoint to the antsibull-docs script."""

import os
import os.path

from ... import app_context
from ...jinja2.environment import doc_environment
from ...logging import log


mlog = log.fields(mod=__name__)


TEMPLATES = [
    '.gitignore',
    'build.sh',
    'conf.py',
    'requirements.txt',
    'rst/index.rst',
]


def write_file(filename: str, content: str) -> None:
    """
    Write content into a file.
    """
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            existing_content = f.read()
        if existing_content == content:
            print(f'Skipping {filename}')
            return

    print(f'Writing {filename}...')
    with open(filename, 'w') as f:
        f.write(content)


def site_init() -> int:
    """
    Initialize a Sphinx site template for a collection docsite.

    Creates a Sphinx configuration file, requirements.txt and a bash script which uses
    antsibull-docs to build the RST files for the specified collections.

    :returns: A return code for the program.  See :func:`antsibull.cli.antsibull_docs.main` for
        details on what each code means.
    """
    flog = mlog.fields(func='site_init')
    flog.notice('Begin site init')

    app_ctx = app_context.app_ctx.get()

    dest_dir = app_ctx.extra['dest_dir']
    collections = app_ctx.extra['collections']
    collection_version = app_ctx.extra['collection_version']
    use_current = app_ctx.extra['use_current']
    squash_hierarchy = app_ctx.extra['squash_hierarchy']

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    elif not os.path.isdir(dest_dir):
        print(f'Expecting {dest_dir} to be a directory')
        return 3

    env = doc_environment(('antsibull.data', 'sphinx_init'))

    for filename in TEMPLATES:
        source = filename.replace('.', '_').replace('/', '_') + '.j2'
        template = env.get_template(source)

        content = template.render(
            dest_dir=dest_dir,
            collection_version=collection_version,
            use_current=use_current,
            squash_hierarchy=squash_hierarchy,
            collections=collections,
        ) + '\n'

        destination = os.path.join(dest_dir, filename)
        destination_path = os.path.dirname(destination)
        if not os.path.exists(destination_path):
            os.makedirs(destination_path)
        write_file(destination, content)

        # Make scripts executable
        if filename.endswith('.sh'):
            os.chmod(destination, 0o755)

    return 0
