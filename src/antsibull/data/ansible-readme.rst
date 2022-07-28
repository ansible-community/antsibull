..
  GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
  SPDX-License-Identifier: GPL-3.0-or-later
  SPDX-FileCopyrightText: Ansible Project, 2020

|PyPI version| |Docs badge| |Chat badge| |Build Status| |Code Of Conduct| |Mailing Lists| |License|

*******
Ansible
*******

Ansible is a radically simple IT automation system. It handles configuration management, application
deployment, cloud provisioning, ad-hoc task execution, network automation, and multi-node
orchestration. Ansible makes complex changes like zero-downtime rolling updates with load balancers
easy. More information on the Ansible `website <https://ansible.com/>`_.

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

See `COPYING <COPYING>`_ to see the full text.

.. |PyPI version| image:: https://img.shields.io/pypi/v/ansible.svg
   :target: https://pypi.org/project/ansible
.. |Docs badge| image:: https://img.shields.io/badge/docs-latest-brightgreen.svg
   :target: https://docs.ansible.com/ansible/latest/
.. |Build Status| image:: https://dev.azure.com/ansible/ansible/_apis/build/status/CI?branchName=devel
   :target: https://dev.azure.com/ansible/ansible/_build/latest?definitionId=20&branchName=devel
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
