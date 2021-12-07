********
Overview
********

This is **work in progress**.

For more information see `Ansible Collections Overview <https://github.com/ansible-collections/overview/blob/master/README.rst>`_.

Feedback welcome via GitHub issues in this repo.


Building the Ansible package
============================


Setup for running from source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

antsibull uses the ``poetry`` tool to build and install::

    # We have had reports of failed builds using macOS, you may want to consider using the ``python:3.9.1`` docker image if you are running macOS to build.

    # Install poetry
    python3 -m pip install poetry

    # Clone the antsibull repo.
    git clone https://github.com/ansible-community/antsibull.git
    cd antsibull

    # Creates a venv with all of the requirements
    poetry install

When running from source, you need to use poetry to run :cmd:`antsibull-build`.  For instance,
``poetry run antsibull-build new-ansible 2.10.0 --data-dir ansible-build-data/2.10``.
So just prepend ``poetry run`` to all of the :cmd:`antsibull-build` commands in the instructions
below.


Building Ansible
~~~~~~~~~~~~~~~~

Setup for building the first time
`````````````````````````````````

If you haven't built Ansible before, you'll need a checkout of the `ansible-build-data <https://github.com/ansible-community/ansible-build-data>`_ repo.  This
repo is where information about the release is saved:

.. code-block:: shell

    # Setup steps for building for the first time:
    git clone git@github.com:ansible-community/ansible-build-data.git

    # Fork and clone github.com/ansible/ansible
    git clone git@github.com:${USER}/ansible.git

Building the tarball
````````````````````

All alpha releases and the first beta
-------------------------------------

.. code-block:: shell

    # Create a directory to output tarballs
    mkdir built

    # Generate the list of compatible versions.
    antsibull-build new-ansible 3.0.0a1 --data-dir ansible-build-data/3

    # Prepare the ansible release
    # (This generates the dependency file and updates changelog.yaml)
    antsibull-build prepare 3.0.0a1 --data-dir ansible-build-data/3

    # Create the ansible release
    # (This generates a single tarball for ansible with a dep on the ansible-core package)
    antsibull-build rebuild-single 3.0.0a1 --data-dir ansible-build-data/3 --sdist-dir built --debian


Setup for the first beta release
---------------------------------

We want to create the directory for the **next** major release when the first beta of this release
is made.  That way, there's no period when we're frozen with no place for new collections to go.

.. code-block:: shell

    # If the current version is 5:
    mkdir ansible-build-data/6
    cd ansible-build-data/6
    # Copy from previous version
    cp ../5/ansible.in .
    cp ../5/collection-meta.yaml .
    # Link initial release of previous version as changelog ancestor
    ln -s ../5/ansible-5.0.0.deps ancestor.deps
    # Create changelog stub with ancestor
    echo -e "ancestor: 5.0.0\nreleases: {}" > changelog.yaml
    # Make any additions or subtractions to the set of collections in the ansible.in file


Beta2 up to and including rc1
-----------------------------

.. code-block:: shell

    # Create a directory to output tarballs
    rm -rf built
    mkdir built

    # Prepare the ansible release
    # (This generates the dependency file and updates changelog.yaml)
    antsibull-build prepare 3.0.0b2 --feature-frozen --data-dir ansible-build-data/3

    # Create the ansible release
    # (This generates a single tarball for ansible with a dep on the ansible-core package)
    antsibull-build rebuild-single 3.0.0b2 --data-dir ansible-build-data/3 --sdist-dir built --debian


Any subsequent rcs and final
----------------------------

.. code-block:: shell

    # Copy the previous rc's .deps file to the new rc version
    cp ansible-build-data/3/ansible-3.0.0rc1.deps ansible-build-data/3/ansible-3.0.0rc2.deps

    # We do not run antsibull-build prepare because the compatible collection version information
    # is now set until final.
    # * Change the _ansible_version field to the new version
    # * If ansible-core needs a version update, change it in the .build and .deps file.
    # * If any collections have been granted an update exception, change the range manually in the
    #   .build and .deps file.
    # vim ansible-build-data/3/ansible-3.build
    # vim ansible-build-data/3/ansible-3.0.0rc2.deps

    # Build it:
    antsibull-build rebuild-single 3.0.0rc2 --data-dir ansible-build-data/3 --build-file ansible-3.build --deps-file ansible-3.0.0rc2.deps --sdist-dir built --debian


New minor releases (3.Y.0)
--------------------------

.. code-block:: shell

    # Create a directory to output tarballs
    rm -rf built
    mkdir built

    # Prepare the ansible release
    # (This generates the dependency file and updates changelog.yaml)
    antsibull-build prepare 3.1.0 --data-dir ansible-build-data/3

    # Until we get separate versions for ansible-core working correctly:
    # https://github.com/ansible-community/antsibull/issues/187
    # We'll need to update the ansible-core version manually. Follow
    # these steps after running antsibull-build prepare above:
    # vim ansible-build-data/3/ansible-3.1.0.deps
    # Change the ansible-core version information in here to the latest compatible version on pypi

    # Create the ansible release
    # (This generates a single tarball for ansible with a dep on the ansible-core package)
    antsibull-build rebuild-single 3.1.0 --data-dir ansible-build-data/3 --build-file ansible-3.build --deps-file ansible-3.1.0.deps --sdist-dir built --debian


Recording release information
`````````````````````````````

.. code-block:: shell

    # Update the porting guide (check for breaking changes)
    cp ansible-build-data/3/porting_guide_3.rst ansible/docs/docsite/rst/porting_guides/
    cd ansible
    git checkout -b update-porting-guide
    # If this is a brand new major release, add the new porting guide to:
    #   ansible/docs/docsite/rst/porting_guides/porting_guides.rst
    git add docs/docsite/rst/porting_guides/
    git commit -m 'Update the porting guide for a new ansible version'
    # git push and open a PR
    cd ..

    # Record the files used to build:
    export ANSIBLE_VERSION=3.0.0a1
    cd ansible-build-data/3
    git add ansible-3.build porting_guide_3.rst "ansible-$ANSIBLE_VERSION.deps" changelog.yaml CHANGELOG-v3.rst
    git commit -m "Collection dependency information for ansible $ANSIBLE_VERSION"
    git push
    git tag $ANSIBLE_VERSION
    git push --tags
    cd ../..

    # Then we can test installation with pip:
    python -m pip install --user built/ansible-3.0.0a1.tar.gz

    ansible -m ansible.posix.synchronize -a 'src=/etc/skel dest=/var/tmp/testing-ansible' localhost


Final Publishing
````````````````

We want to sync docs and releases.  So the first thing to do is to alert the docs team in
``#ansible-docs`` that we're making a release (they should know ahead of time if they're watching the
schedule too).

* In minor/patch releases, check the porting guide for unwanted (breaking) changes (collections that are
  new in this patch release are allowed to have breaking changes but existing collections should not.)

  * Fixing this requires manually changing the .deps file and re-running rebuild-single (and then
    pinging the collection maintainer to find out what should happen for the next release.)

* Merge the porting guide PR.
* Build Ansible Docs to docs.ansible.com
* Upload the tarball to pypi::

    twine upload --sign built/ansible-3.0.0.tar.gz


Announcing Ansible
~~~~~~~~~~~~~~~~~~

* Copy the previous ansible release announcement from the ansible-devel google group.
* Change the version numbers.
* Change the sha256sum
* Add any info specific to this release.

  * Send any important information (like one-off changes to the release schedule) from here to

    `The Bullhorn <https://github.com/ansible/community/issues/546>`_

For alphas, send to ansible-devel@googlegroups.com

For betas and rcs, send to ansible-devel and ansible-project@googlegroups.com

For final, send to ansible-devel, ansible-project, and ansible-announce.

Post a link to the mailing list post to the #ansible and #ansible-devel irc channels.

For all, post the link to Reddit

Update the topic in the #ansible channel with the new version

TODO
====

* Right now the script assumes ansible-core and ansible will have the same version.  This is true
  for 2.10 and possibly for 3 but in the longer term ansible-core major releases are going to
  slow down while ansible releases may speed up slightly.  We'll need to adapt the script to handle
  these diverged versions.
