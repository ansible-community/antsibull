..
  Copyright (c) Ansible Project
  GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
  SPDX-License-Identifier: GPL-3.0-or-later

.. automodule:: antsibull.schemas.docs.base

There is a dictionary named ANSIBLE_DOC_SCHEMAS to allow you easier access to these
programmatically.  It is a mapping of plugin types to the ansible_doc schema which handle it.
For example, this is the entry for modules:

.. code-block: python

    {'module': ModulePluginSchema}


?If you want to validate individual plugins, use antsibull.schemas.docs?
:${PLUGIN_TYPE}Schema: if you want to validate individual sections of the ansible-doc output (doc,
    examples, metadata, return)

If you want to validate individual sections of plugins, retrieve the individual components of
the schema from the higher level schema you imported.
.. code-block:: yaml
    module:
        top: ModulePluginSchema
        doc: ModuleDocSchema
        examples: PluginExamplesSchema
        metadata: PluginMetadataSchema
        return: PluginReturnSchema


Lowlevel
========

These are the implementation details.  Most Ansible plugins share a common documentation format.
Thus, there are only three sets of classes here.  As a user, you will likely not use these directly.
Use one of the upper ones instead.  As a contributor looking to modify the schemas, this is useful
information as it explains how the functionality is implemented.

* Callback -- Ansible Callback Plugin Documentation
* Module -- Ansible Module Documentation
* Plugin -- Generic Plugins.  The remaining plugins are aliases to this set of classes in the higher
  level interfaces.
