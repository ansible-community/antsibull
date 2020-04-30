********
Overview
********

This is **work in progress**.

For more information see `Ansible Collections Overview <https://github.com/ansible-collections/overview/blob/master/README.rst>`_.

Feedback welcome via GitHub issues in this repo.

Building Ansible
================

The script needs python-3.8 or later.

Here's some steps to test the build process:

::
    # Setup steps
    git clone git@github.com:ansible-community/ansible-build-data
    mkdir ansible-build-data/2.10
    cp acd.in ansible-build-data/2.10
    mkdir built
    python3.8 -m pip install -r requirements.txt --user

    # Generate the list of compatible versions.  Intended to be run when we feature freeze
    python3.8 build-acd.py new-acd 2.10.0 --dest-dir ansible-build-data/2.10

    # Create an ansible release using one of the following:
    # Single tarball for ansible with a dep on the ansible-base package
    python3.8 build-acd.py build-single 2.10.0 --build-file ansible-build-data/2.10/acd-2.10.build --deps-file ansible-build-data/2.10/acd-2.10.0.deps --dest-dir built
    # One tarball per collection plus the ansible package which deps on all of them and ansible-base
    python3.8 build-acd.py build-multiple 2.10.0 --build-file ansible-build-data/2.10/acd-2.10.build --deps-file ansible-build-data/2.10/acd-2.10.0.deps --dest-dir built

    # Create a collection that can be installed to pull in all of the collections
    python3.8 build-acd.py build-collection 2.10.0 --deps-file ansible-build-data/2.10/acd-2.10.0.deps --dest-dir built

    # Record the files used to build:
    cd ansible-build-data/2.10
    git add acd-2.10.build
    git commit -m 'Collection dependency information for ansible 2.10.x and ansible-2.10.0'
    git push

    # Then we can test installation with pip:
    # This might not work:
    python -m pip install --user git+https://github.com/ansible/ansible.git#egg=ansible-base

    # But this should
    python -m pip install --user built/ansible-2.10.0.tar.gz
    # And this should once it is uploaded to test pypi
    python3.8 -m pip install --user --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ansible

    ansible -m ansible.posix.synchronize -a 'src=/etc/skel dest=/var/tmp/testing-acd' localhost


Using a pre-release build
=========================

We have uploaded test versions of the ansible and ansible-base package **for testing only**.  You
should be able to upgrade your ansible install like::

    python3.8 -m pip install --user --upgrade --extra-index-url https://toshio.fedorapeople.org/ansible/acd/ ansible

And it will pull in both the ``ansible`` and ``ansible-base`` Python packages .

For offline install, one way to get that would be to download the two tarballs that are there
and pip install them as files.

TODO
====

* Right now the script assumes ansible-base and ansible will have the same version.  This is true
  for 2.10 and possibly for 2.11 but in the longer term ansible-base major releases are going to
  slow down while ansible releases may speed up slightly.  We'll need to adapt the script to handle
  these diverged versions.

* The way we specify release compatibility does not allow pre-release package dependencies to work.
  (ie: if we have a dependency on ansible-2.4.x, it will not pick up ansible-2.4.0rc1 as satisfying
  the dependency)  We should try to fix this to make testing easier.  Something like the following
  should work::

    'ansible-base>=2.4.0a0,<2.5'

  * Do we want to do the same thing with collections?
