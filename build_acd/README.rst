********
Overview
********

This is **work in progress**.

For more information see `Ansible Collections Overview <https://github.com/ansible-collections/overview/blob/master/README.rst>`_.

Feedback welcome via GitHub issues in this repo.

Building ACD
=============

Here's some steps to test the build process:

::

    python3.8 -m pip install -r build-acd-requirements.txt --user
    mkdir built
    python3.8 build-acd.py new-acd 2.10.0 --dest-dir built
    python3.8 build-acd.py build-single 2.10.0 --build-file built/acd-2.10.build --dest-dir built
    # Create a collection that can be installed to pull in all of the collections
    python3.8 build-acd.py build-collection 2.10.0 --deps-file built/acd-2.10.0.deps --dest-dir built

    # Once this is uploaded to pypi or testpypi, we can test installing the ansible-2.10.0.tar.gz
    # using pip to resolve the requirement on ansible-base
    python -m pip install --user git+https://github.com/ansible/ansible.git#egg=ansible-base
    python -m pip install --user built/ansible-2.10.0.tar.gz

    ansible -m ansible.posix.synchronize -a 'src=/etc/skel dest=/var/tmp/testing-acd' localhost

Using a pre-release build
=========================

We have uploaded test versions of the ansible and ansible-base package **for testing only**.  You
should be able to upgrade your ansible install like::

    python3.8 -m pip install --user --upgrade -i https://toshio.fedorapeople.org/ansible/acd/ ansible

And it will pull in both the ``ansible`` and ``ansible-base`` Python packages .

For offline install, one way to get that would be to download the two tarballs that are there
and pip install them as files.
