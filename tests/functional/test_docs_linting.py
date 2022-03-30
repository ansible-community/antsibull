import io
import os

from contextlib import redirect_stdout

from antsibull.cli.antsibull_docs import run


def write_file(path, content):
    with open(path, 'wb') as f:
        f.write(content)


def test_docsite_linting_success(tmp_path_factory):
    dir = tmp_path_factory.mktemp('foobar')
    write_file(dir / 'galaxy.yml', b'''
namespace: foo
name: bar
''')
    docsite_dir = dir / 'docs' / 'docsite'
    docsite_rst_dir = docsite_dir / 'rst'
    os.makedirs(docsite_rst_dir)
    write_file(docsite_dir / 'extra-docs.yml', b'''
sections:
  - title: Foo
    toctree:
      - foo

''')
    write_file(docsite_dir / 'links.yml', b'''
edit_on_github:
  repository: ansible-collections/foo.bar
  branch: main
  path_prefix: ''

extra_links:
  - description: Submit an issue
    url: https://github.com/ansible-collections/foo.bar/issues/new

communication:
  matrix_rooms:
    - topic: General usage and support questions
      room: '#users:ansible.im'
  irc_channels:
    - topic: General usage and support questions
      network: Libera
      channel: '#ansible'
  mailing_lists:
    - topic: Ansible Project List
      url: https://groups.google.com/g/ansible-project
''')
    write_file(docsite_rst_dir / 'foo.rst', b'''
_ansible_collections.foo.bar.docsite.bla:

Foo bar
=======

Baz bam :ref:`myself <ansible_collections.foo.bar.docsite.bla>`.
''')

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        rc = run(['antsibull-docs', 'lint-collection-docs', str(dir)])
    stdout = stdout.getvalue().splitlines()
    print('\n'.join(stdout))
    assert rc == 0
    assert stdout == []


def test_docsite_linting_failure(tmp_path_factory):
    dir = tmp_path_factory.mktemp('foo.bar')
    write_file(dir / 'galaxy.yml', b'''
namespace: foo
name: bar
''')
    docsite_dir = dir / 'docs' / 'docsite'
    docsite_rst_dir = docsite_dir / 'rst'
    os.makedirs(docsite_rst_dir)
    extra_docs = docsite_dir / 'extra-docs.yml'
    write_file(extra_docs, b'''
sections:
  - title: Foo
    toctree:
      - foo
      - fooooo
  - foo: bar
    toctree:
      baz: bam
''')
    links = docsite_dir / 'links.yml'
    write_file(links, b'''
foo: bar

edit_on_github:
  repository: ansible-collections/foo.bar
  path_prefix: 1

extra_links:
  - description: Submit an issue
    url: https://github.com/ansible-collections/foo.bar/issues/new
  - url: bar

communication:
  matrix_rooms:
    - topic: General usage and support questions
      room: '#users:ansible.im'
  irc_channel:
    - topic: General usage and support questions
      network: Libera
      channel: '#ansible'
  mailing_lists:
    - topic: Ansible Project List
      url: https://groups.google.com/g/ansible-project
''')
    write_file(docsite_rst_dir / 'foo.rst', b'''
_ansible_collections.foo.bar.docsite.bla:

Foo bar
=======

Baz bam :ref:`myself <ansible_collections.foo.bar.docsite.bla>`.
''')

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        rc = run(['antsibull-docs', 'lint-collection-docs', str(dir)])
    stdout = stdout.getvalue().splitlines()
    print('\n'.join(stdout))
    assert rc == 3
    assert stdout == [
        f'{extra_docs}:0:0: Section #1 has no "title" entry',
        f'{links}:0:0: communication -> irc_channel: extra fields not permitted (type=value_error.extra)',
        f'{links}:0:0: edit_on_github -> branch: field required (type=value_error.missing)',
        f'{links}:0:0: extra_links -> 1 -> description: field required (type=value_error.missing)',
        f'{links}:0:0: foo: extra fields not permitted (type=value_error.extra)',
    ]
