# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""
Schemas for the plugin DOCUMENTATION data.

This is a highlevel interface.  The hope is that developers can use either this or
antsibull.schemas.docs to handle all of their validation needs.
"""

# Ignore Unitialized attribute errors because BaseModel works some magic
# to initialize the attributes when data is loaded into them.
# pyre-ignore-all-errors[13]

import typing as t

from .base import BaseModel
from .callback import CallbackSchema
from .module import ModuleSchema
from .plugin import PluginSchema
from .role import RoleSchema


__all__ = ('ANSIBLE_DOC_SCHEMAS', 'AnsibleDocSchema', 'BecomePluginSchema', 'CachePluginSchema',
           'CallbackPluginSchema', 'CliConfPluginSchema', 'ConnectionPluginSchema',
           'HttpApiPluginSchema', 'InventoryPluginSchema', 'LookupPluginSchema',
           'ModulePluginSchema', 'NetConfPluginSchema', 'ShellPluginSchema', 'StrategyPluginSchema',
           'VarsPluginSchema',)


class AnsibleDocSchema(BaseModel):
    """
    Document the output that comes back from ansible-doc.

    This schema is a constructed schema.  It imagines that the user has accumulated the output from
    repeated runs of ansible-doc in a dict layed out roughly like this:

    .. code-block:: yaml

        plugin_type:
            plugin_name:
                # json.loads(ansible-doc -t plugin_type --json plugin_name)

    Pass the dict above to :meth:`AnsibleDocSchema.parse_obj` to build the models from the schema.

    If you want to use the Schema to validate and normalize the data but need a :python:obj:`dict`
    afterwards, call :meth:`AnsibleDocSchema.dict` on the populated model to get
    a :python:obj:`dict` back out.
    """

    become: t.Dict[str, PluginSchema]
    cache: t.Dict[str, PluginSchema]
    callback: t.Dict[str, CallbackSchema]
    cliconf: t.Dict[str, PluginSchema]
    connection: t.Dict[str, PluginSchema]
    httpapi: t.Dict[str, PluginSchema]
    inventory: t.Dict[str, PluginSchema]
    lookup: t.Dict[str, PluginSchema]
    module: t.Dict[str, ModuleSchema]
    netconf: t.Dict[str, PluginSchema]
    shell: t.Dict[str, PluginSchema]
    strategy: t.Dict[str, PluginSchema]
    vars: t.Dict[str, PluginSchema]
    role: t.Dict[str, RoleSchema]


class GenericPluginSchema(BaseModel):
    """
    Document the output of ``ansible-doc -t PLUGIN_TYPE PLUGIN_NAME``.

    .. note:: Both the model and the dict will be wrapped in an outer dict with your data mapped
        to the ``__root__`` key. This happens because the toplevel key of ansible-doc's output is
        a dynamic key which we can't automatically map to an attribute name.
    """

    __root__: t.Dict[str, PluginSchema]


class CallbackPluginSchema(BaseModel):
    """
    Document the output of ``ansible-doc -t callback CALLBACK_NAME``.

    .. note:: Both the model and the dict will be wrapped in an outer dict with your data mapped
        to the ``__root__`` key. This happens because the toplevel key of ansible-doc's output is
        a dynamic key which we can't automatically map to an attribute name.
    """

    __root__: t.Dict[str, CallbackSchema]


class ModulePluginSchema(BaseModel):
    """
    Document the output of ``ansible-doc -t module MODULE_NAME``.

    .. note:: Both the model and the dict will be wrapped in an outer dict with your data mapped
        to the ``__root__`` key. This happens because the toplevel key of ansible-doc's output is
        a dynamic key which we can't automatically map to an attribute name.
    """

    __root__: t.Dict[str, ModuleSchema]


class RolePluginSchema(BaseModel):
    """
    Document the output of ``ansible-doc -t role ROLE_NAME``.

    .. note:: Both the model and the dict will be wrapped in an outer dict with your data mapped
        to the ``__root__`` key. This happens because the toplevel key of ansible-doc's output is
        a dynamic key which we can't automatically map to an attribute name.
    """

    __root__: t.Dict[str, RoleSchema]


#: Make sure users can access plugins using the plugin type rather than having to guess that
#: these types use the GenericPluginSchema
BecomePluginSchema = GenericPluginSchema
CachePluginSchema = GenericPluginSchema
CliConfPluginSchema = GenericPluginSchema
ConnectionPluginSchema = GenericPluginSchema
HttpApiPluginSchema = GenericPluginSchema
InventoryPluginSchema = GenericPluginSchema
LookupPluginSchema = GenericPluginSchema
NetConfPluginSchema = GenericPluginSchema
ShellPluginSchema = GenericPluginSchema
StrategyPluginSchema = GenericPluginSchema
VarsPluginSchema = GenericPluginSchema


#: A mapping from plugin type to the Schema to use for them.  Use this to more easily get
#: the Schema programmatically.
ANSIBLE_DOC_SCHEMAS = {
    'become': BecomePluginSchema,
    'cache': CachePluginSchema,
    'callback': CallbackPluginSchema,
    'cliconf': CliConfPluginSchema,
    'connection': ConnectionPluginSchema,
    'httpapi': HttpApiPluginSchema,
    'inventory': InventoryPluginSchema,
    'lookup': LookupPluginSchema,
    'module': ModulePluginSchema,
    'netconf': NetConfPluginSchema,
    'role': RolePluginSchema,
    'shell': ShellPluginSchema,
    'strategy': StrategyPluginSchema,
    'vars': VarsPluginSchema,
}
