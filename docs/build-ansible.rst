********
Overview
********

This is **work in progress**.

For more information see `Ansible Collections Overview <https://github.com/ansible-collections/overview/blob/master/README.rst>`_.

Feedback welcome via GitHub issues in this repo.


Building the Ansible package
============================

.. note::
    * The script needs python-3.8 or later.


Setup for running from source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

antsibull uses the ``poetry`` tool to build and install.

::
    # Install poetry
    python3 -m pip install poetry

    # Clone the antisbull repo.
    git clone https://github.com/ansible-comunity/antsibull
    cd antsibull

    # Creates a venv with all of the requirements
    poetry install

When running from source, you need to use poetry to run :cmd:`antsibull-build`.  For instance,
``poetry run antsibull-build new-ansible 2.10.0 --data-dir ansi ble-build-data/2.10``.
So just prepend ``poetry run`` to all of the :cmd:`antsibull-build` commands in the instructions
below.


Building Ansible
~~~~~~~~~~~~~~~~

Setup for the first alpha release
---------------------------------
::
    # Setup steps for building for the first time:
    git clone git@github.com:ansible-community/ansible-build-data
    mkdir ansible-build-data/2.11
    # Copy from previous version
    cp ansible-build-data/2.10/ansible.in ansible-build-data/2.11/
    # Make any additions or subtractions to the set of collections in the ansible.in file


All alpha releases and the first beta
-------------------------------------
::
    # Create a directory to output tarballs
    mkdir built

    # Generate the list of compatible versions.
    antsibull-build new-ansible 2.11.0a1 --data-dir ansible-build-data/2.11

    # Create the ansible release
    # (This generates a single tarball for ansible with a dep on the ansible-base package)
    antsibull-build single 2.11.0 --data-dir ansible-build-data/2.11 --sdist-dir built

    # Record the files used to build:
    cd ansible-build-data/2.11
    git add ansible-2.11a1.build ansible-2.11.0a1.deps changelog.yaml CHANGELOG-v2.11.rst
    git commit -m 'Collection dependency information for ansible 2.11.x and ansible-2.11.0'
    git push
    git tag 2.11.0a1
    git push --tags

    # Update the porting guide
    cp ansible-build-data/2.11/porting_guide_2.11.rst ansible/docs/docsite/rst/porting_guide/
    cd ansible
    git checkout -b update-porting-guide
    git add ansible/docs/docsite/rst/porting_guide/
    git commit -a -m 'Update the porting guide for a new ansible version'
    # git push and open a PR

    # Then we can test installation with pip:
    python -m pip install --user built/ansible-2.11.0a1.tar.gz

    ansible -m ansible.posix.synchronize -a 'src=/etc/skel dest=/var/tmp/testing-ansible' localhost

    # Upload to pypi:
    twine upload built/ansible-2.11.0a1.tar.gz


Beta2 up to and including rc1
-----------------------------
::
    # Create a directory to output tarballs
    rm -rf built
    mkdir built

    # We do not run antsibull-build single because the compatible collection version information
    # is now set until final.
    # If ansible-base needs a version update, change it in the .build file.
    # If any collections have been granted an update exception, change the range manually in the
    # .build file.

    # Create the ansible release
    # (This generates a single tarball for ansible with a dep on the ansible-base package)
    antsibull-build single 2.11.0b2 --feature-frozen --data-dir ansible-build-data/2.11 --sdist-dir built

    # Record the files used to build:
    cd ansible-build-data/2.11
    git add ansible-2.11.0b2.deps changelog.yaml CHANGELOG-v2.11.rst
    # Also git add the .build file if any manual changes were made
    git commit -m 'Collection dependency information for ansible-2.11.0b2'
    git push
    git tag 2.11.0b2
    git push --tags

    # Update the porting guide
    cp ansible-build-data/2.11/porting_guide_2.11.rst ansible/docs/docsite/rst/porting_guide/
    cd ansible
    git checkout -b update-porting-guide
    git add ansible/docs/docsite/rst/porting_guide/
    git commit -a -m 'Update the porting guide for a new ansible version'
    # git push and open a PR

    # Then we can test installation with pip:
    python -m pip install --user built/ansible-2.11.0b2.tar.gz

    ansible -m ansible.posix.synchronize -a 'src=/etc/skel dest=/var/tmp/testing-ansible' localhost

    # Upload to pypi:
    twine upload built/ansible-2.11.0b2.tar.gz


Any subsequent rcs and final
----------------------------
::
    # Copy the previous rc's .deps file to the new rc version
    cp ansible-build-data/ansible-2.11.0rc1.deps ansible-build-data/ansible-2.11.0rc2.deps

    # Modify it if needed to manually update versions
    # vim ansible-build-data/ansible-2.11.0rc2.deps

    # Build it:
    antsibull-build rebuild-single 2.11.0rc2 --build-data-dir ansible-build-data/2.11 --build-file ansible-2.11.build --dest-dir built


New patch releases (2.11.Z)
---------------------------
::
    # Create a directory to output tarballs
    rm -rf built
    mkdir built

    # We do not run antsibull-build single because the compatible collection version information
    # is now set until final.

    # Create the ansible release
    # (This generates a single tarball for ansible with a dep on the ansible-base package)
    antsibull-build single 2.11.1 --data-dir ansible-build-data/2.11 --sdist-dir built

    # Record the files used to build:
    cd ansible-build-data/2.11
    git add ansible-2.11.1.deps changelog.yaml CHANGELOG-v2.11.rst
    git commit -m 'Collection dependency information for ansible 2.11.x and ansible-2.11.1'
    git push
    git tag 2.11.1
    git push --tags

    # Update the porting guide
    cp ansible-build-data/2.11/porting_guide_2.11.rst ansible/docs/docsite/rst/porting_guide/
    cd ansible
    git checkout -b update-porting-guide
    git add ansible/docs/docsite/rst/porting_guide/
    git commit -a -m 'Update the porting guide for a new ansible version'
    # git push and open a PR

    # Then we can test installation with pip:
    python -m pip install --user built/ansible-2.11.1.tar.gz

    ansible -m ansible.posix.synchronize -a 'src=/etc/skel dest=/var/tmp/testing-ansible' localhost

    # Upload to pypi:
    twine upload built/ansible-2.11.1.tar.gz


Announcing Ansible
~~~~~~~~~~~~~~~~~~

* Copy the previous ansible release announcement from the ansible-devel google group.
* Change the version numbers.
* Change the sha256sum
* Add any info specific to this release.

For alphas, send to ansible-devel@googlegroups.com

For betas and rcs, send to ansible-devel and ansible-project@googlegroups.com

For final, send to ansible-devel, ansible-project, and ansible-announce.

Post a link to the mailing list post to the #ansible and #ansible-devel irc channels.


TODO
====

* Right now the script assumes ansible-base and ansible will have the same version.  This is true
  for 2.10 and possibly for 2.11 but in the longer term ansible-base major releases are going to
  slow down while ansible releases may speed up slightly.  We'll need to adapt the script to handle
  these diverged versions.
