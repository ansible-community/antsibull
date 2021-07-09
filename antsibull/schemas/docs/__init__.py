# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""
Schemas for the plugin DOCUMENTATION data.

This is a highlevel interface.  The hope is that developers can use either this or
antsibull.schemas.docs.ansible_doc to handle all of their validation needs.
"""

from .callback import CallbackDocSchema, CallbackSchema
from .module import ModuleDocSchema, ModuleSchema
from .plugin import (PluginDocSchema, PluginExamplesSchema,
                     PluginMetadataSchema, PluginReturnSchema, PluginSchema)

BecomeSchema = PluginSchema
CacheSchema = PluginSchema
CliConfSchema = PluginSchema
ConnectionSchema = PluginSchema
HttpApiSchema = PluginSchema
InventorySchema = PluginSchema
LookupSchema = PluginSchema
NetConfSchema = PluginSchema
ShellSchema = PluginSchema
StrategySchema = PluginSchema
VarsSchema = PluginSchema


#: The schemas that most plugins use to validate and normalize their documentation.
_PLUGIN_SCHEMA_RECORD = {
    'top': PluginSchema,
    'doc': PluginDocSchema,
    'examples': PluginExamplesSchema,
    'metadata': PluginMetadataSchema,
    'return': PluginReturnSchema,
}


#: Mapping of plugin_types to the schemas which validate and normalize their documentation.
#: The structure of this mapping is a two level nested dict.  The outer key is the plugin_type.
#: The inner keys are the sections of the documentation (doc, example, metadata, return, or top
#: [which combines all of hte above, such as ansible-doc returns]) to validate.
DOCS_SCHEMAS = {
    'become': _PLUGIN_SCHEMA_RECORD,
    'cache': _PLUGIN_SCHEMA_RECORD,
    'callback': {
        'top': CallbackSchema,
        'doc': CallbackDocSchema,
        'examples': PluginExamplesSchema,
        'metadata': PluginMetadataSchema,
        'return': PluginReturnSchema,
    },
    'cliconf': _PLUGIN_SCHEMA_RECORD,
    'connection': _PLUGIN_SCHEMA_RECORD,
    'httpapi': _PLUGIN_SCHEMA_RECORD,
    'inventory': _PLUGIN_SCHEMA_RECORD,
    'lookup': _PLUGIN_SCHEMA_RECORD,
    'module': {
        'top': ModuleSchema,
        'doc': ModuleDocSchema,
        'examples': PluginExamplesSchema,
        'metadata': PluginMetadataSchema,
        'return': PluginReturnSchema,
    },
    'netconf': _PLUGIN_SCHEMA_RECORD,
    'shell': _PLUGIN_SCHEMA_RECORD,
    'strategy': _PLUGIN_SCHEMA_RECORD,
    'vars': _PLUGIN_SCHEMA_RECORD,
}
