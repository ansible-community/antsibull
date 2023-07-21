..
  GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
  SPDX-License-Identifier: GPL-3.0-or-later
  SPDX-FileCopyrightText: Ansible Project, 2020

|PyPI version| |Docs badge| |Chat badge| |Code Of Conduct| |Mailing Lists| |License|

*******
Ansible
*******

Ansible is a radically simple IT automation system. It handles configuration management, application
deployment, cloud provisioning, ad-hoc task execution, network automation, and multi-node
orchestration. Ansible makes complex changes like zero-downtime rolling updates with load balancers
easy. More information on the Ansible `website <https://ansible.com/>`_.

This is the ``ansible`` community package.
The ``ansible`` python package contains a set of
independent Ansible collections that are curated by the community,
and it pulls in `ansible-core <https://pypi.org/project/ansible-core/>`_.
The ``ansible-core`` python package contains the core runtime and CLI tools,
such as ``ansible`` and ``ansible-playbook``,
while the ``ansible`` package contains extra modules, plugins, and roles.

``ansible`` follows `semantic versioning <https://semver.org/>`_.
Each major version of ``ansible`` depends on a specific major version of
``ansible-core`` and contains specific major versions of the collections it
includes.

Design Principles
=================

*  Have an extremely simple setup process and a minimal learning curve.
*  Manage machines quickly and in parallel.
*  Avoid custom-agents and additional open ports, be agentless by
   leveraging the existing SSH daemon.
*  Describe infrastructure in a language that is both machine and human
   friendly.
*  Focus on security and easy auditability/review/rewriting of content.
*  Manage new remote machines instantly, without bootstrapping any
   software.
*  Allow module development in any dynamic language, not just Python.
*  Be usable as non-root.
*  Be the easiest IT automation system to use, ever.

Use Ansible
===========

You can install a released version of Ansible with ``pip`` or a package manager. See our
`Installation guide <https://docs.ansible.com/ansible/latest/installation_guide/index.html>`_ for details on installing Ansible
on a variety of platforms.

Reporting Issues
================
Issues with plugins and modules in the Ansible package should be reported
on the individual collection's issue tracker.
Issues with ``ansible-core`` should be reported on
the `ansible-core issue tracker <https://github.com/ansible/ansible/issues/>`_.

Refer to the `Communication page
<https://docs.ansible.com/ansible/latest/community/communication.html>`_ for a
list of support channels if you need assistance from the community or are
unsure where to report your issue.


Get Involved
============

*  Read `Community Information <https://docs.ansible.com/ansible/latest/community>`_ for ways to contribute to 
   and interact with the project, including mailing list information and how
   to submit bug reports and code to Ansible or Ansible collections.
*  Join a `Working Group <https://github.com/ansible/community/wiki>`_, an organized community
   devoted to a specific technology domain or platform.
*  Talk to us before making larger changes
   to avoid duplicate efforts. This not only helps everyone
   know what is going on, but it also helps save time and effort if we decide
   some changes are needed.
*  For a list of email lists,  Matrix and IRC channels, and Working Groups, see the
   `Communication page <https://docs.ansible.com/ansible/latest/community/communication.html>`_

Coding Guidelines
=================

We document our Coding Guidelines in the `Developer Guide <https://docs.ansible.com/ansible/devel/dev_guide/>`_. We also suggest you review:

* `Developing modules checklist <https://docs.ansible.com/ansible/devel/dev_guide/developing_modules_checklist.html>`_
* `Collection contributor guide <https://docs.ansible.com/ansible/devel/community/contributions_collections.html>`_

Branch Info
===========

*  The Ansible package is a 'batteries included' package that brings in ``ansible-core`` and a curated set of collections. Ansible uses `semantic versioning <https://semver.org/>`_ (for example, Ansible 5.6.0). 
*  The Ansible package has only one stable branch, called 'latest' in the documentation.
*  See `Ansible release and maintenance <https://docs.ansible.com/ansible/latest/reference_appendices/release_and_maintenance.html>`_  for information about active branches and their corresponding ``ansible-core`` versions.
*  Refer to the
   `ansible-build-data <https://github.com/ansible-community/ansible-build-data/>`_
   repository for the exact versions of ``ansible-core`` and collections that
   are included in each ``ansible`` release.

Roadmap
=======

Based on team and community feedback, an initial roadmap will be published for a major 
version (example: 5, 6).  The `Ansible Roadmap 
<https://docs.ansible.com/ansible/devel/roadmap/ansible_roadmap_index.html>`_ details what is planned and how to influence the
roadmap.

Authors
=======

Ansible was created by `Michael DeHaan <https://github.com/mpdehaan>`_
and has contributions from over 4700 users (and growing). Thanks everyone!

`Ansible <https://www.ansible.com>`_ is sponsored by `Red Hat, Inc.
<https://www.redhat.com>`_

License
=======

GNU General Public License v3.0 or later

See `COPYING <https://github.com/ansible-community/antsibull/blob/main/src/antsibull/data/gplv3.txt>`_
for the full license text.

.. |PyPI version| image:: https://img.shields.io/pypi/v/ansible.svg
   :target: https://pypi.org/project/ansible
.. |Docs badge| image:: https://img.shields.io/badge/docs-latest-brightgreen.svg
   :target: https://docs.ansible.com/ansible/latest/
.. |Chat badge| image:: https://img.shields.io/badge/chat-IRC-brightgreen.svg
   :target: https://docs.ansible.com/ansible/latest/community/communication.html
.. |Code Of Conduct| image:: https://img.shields.io/badge/code%20of%20conduct-Ansible-silver.svg
   :target: https://docs.ansible.com/ansible/latest/community/code_of_conduct.html
   :alt: Ansible Code of Conduct
.. |Mailing Lists| image:: https://img.shields.io/badge/mailing%20lists-Ansible-orange.svg
   :target: https://docs.ansible.com/ansible/latest/community/communication.html#mailing-list-information
   :alt: Ansible mailing lists
.. |License| image:: https://img.shields.io/badge/license-GPL%20v3.0-brightgreen.svg
   :target: COPYING
   :alt: Repository License
