********
Overview
********

This is **work in progress**.

For more information see `Ansible Collections Overview <https://github.com/ansible-collections/overview/blob/master/README.rst>`_.

Feedback welcome via GitHub issues in this repo.

Building Ansible
================

The script needs python-3.8 or later.

Here's some steps to test the build process.  These are steps for running from source.  If the
package is installed, you won't need to know about poetry at all::

    # Setup steps for building for the first time:
    git clone git@github.com:ansible-community/ansible-build-data
    mkdir ansible-build-data/2.10
    # Copy from previous version... already done for 2.10
    # cp ansible-build-data/2.10/ansible.in ansible-build-data/2.10
    mkdir built

    # Creates a venv with all of the requirements
    poetry install

    # Generate the list of compatible versions.  Intended to be run when we feature freeze
    poetry run antsibull-build new-ansible 2.10.0 --dest-dir ansible-build-data/2.10

    # Create an ansible release using *one* of the following:
    # Single tarball for ansible with a dep on the ansible-base package
    poetry run antsibull-build single 2.10.0 --build-file ansible-build-data/2.10/ansible-2.10.build --deps-file ansible-build-data/2.10/ansible-2.10.0.deps --dest-dir built
    # One tarball per collection plus the ansible package which deps on all of them and ansible-base
    poetry run antsibull-build multiple 2.10.0 --build-file ansible-build-data/2.10/ansible-2.10.build --deps-file ansible-build-data/2.10/ansible-2.10.0.deps --dest-dir built

    # Create a collection that can be installed to pull in all of the collections
    poetry run antsibull-build collection 2.10.0 --deps-file ansible-build-data/2.10/ansible-2.10.0.deps --dest-dir built

    # Record the files used to build:
    cd ansible-build-data/2.10
    git add ansible-2.10.build ansible-2.10.0.deps
    git commit -m 'Collection dependency information for ansible 2.10.x and ansible-2.10.0'
    git push
    git tag 2.10.0
    git push --tags

    # Update the porting guide
    cp ansible-build-data/2.10/porting_guide_2.10.rst ansible/docs/docsite/rst/porting_guide/
    cd ansible
    git checkout -b update-porting-guide
    git add ansible/docs/docsite/rst/porting_guide/
    git commit -a -m 'Update the porting guide for a new ansible version'
    # git push and open a PR

    # Then we can test installation with pip:
    # This might not work:
    python -m pip install --user git+https://github.com/ansible/ansible.git#egg=ansible-base

    # But this should
    python -m pip install --user built/ansible-2.10.0.tar.gz
    # And this should once it is uploaded to test pypi
    python -m pip install --user --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ansible

    ansible -m ansible.posix.synchronize -a 'src=/etc/skel dest=/var/tmp/testing-ansible' localhost


TODO
====

* Right now the script assumes ansible-base and ansible will have the same version.  This is true
  for 2.10 and possibly for 2.11 but in the longer term ansible-base major releases are going to
  slow down while ansible releases may speed up slightly.  We'll need to adapt the script to handle
  these diverged versions.
