# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Schemas for the plugin DOCUMENTATION data."""

# Ignore Unitialized attribute errors because BaseModel works some magic
# to initialize the attributes when data is loaded into them.
# pyre-ignore-all-errors[13]

import typing as t

from .base import BaseModel
from .callback_docs import CallbackSchema
from .module_docs import ModuleSchema
from .plugin_docs import PluginSchema


class AnsibleDocSchema(BaseModel):
    """
    Document the output that comes back from ansible-doc.

    This schema is a constructed schema.  It imagines that the user has accumulated the output from
    repeated runs of ansible-doc in a dict layed out roughly like this:

    .. code-block:: yaml

        plugin_type:
            plugin_name:
                # json.loads(ansible-doc -t plugin_type --json plugin_name)
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


class GenericPluginSchema(BaseModel):
    """
    Document the output of ``ansible-doc -t PLUGIN_TYPE PLUGIN_NAME``.

    .. note:: Both the model and the dict will be wrapped in an outer dict with your data mapped
        to the ``__root`` key. This happens because the toplevel key of ansible-doc's output is
        a dynamic key which we can't automatically map to an attribute name.
    """

    __root__: t.Dict[str, PluginSchema]


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


class CallbackPluginSchema(BaseModel):
    """
    Document the output of ``ansible-doc -t callback CALLBACK_NAME``.

    .. note:: Both the model and the dict will be wrapped in an outer dict with your data mapped
        to the ``__root`` key. This happens because the toplevel key of ansible-doc's output is
        a dynamic key which we can't automatically map to an attribute name.
    """

    __root__: t.Dict[str, CallbackSchema]


class ModulePluginSchema(BaseModel):
    """
    Document the output of ``ansible-doc -t module MODULE_NAME``.

    .. note:: Both the model and the dict will be wrapped in an outer dict with your data mapped
        to the ``__root`` key. This happens because the toplevel key of ansible-doc's output is
        a dynamic key which we can't automatically map to an attribute name.
    """

    __root__: t.Dict[str, ModuleSchema]
