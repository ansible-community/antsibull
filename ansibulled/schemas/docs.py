# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""
Schemas for the plugin DOCUMENTATION data.

This is a highlevel interface.  The hope is that eventually people can use either this or
ansibulled.  Right now that's probably infeasible because people will want to validate a smaller
piece of the docs so that they can recover from errors (for instance, validate the docs, examples,
metadta, and returndocs separately.  Only fail if docs doesn't validate.
"""

from .plugin import PluginSchema
from .callback import CallbackSchema
from .module import ModuleSchema


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

SCHEMAS = {
    'become': PluginSchema,
    'cache': PluginSchema,
    'callback': CallbackSchema,
    'cliconf': PluginSchema,
    'connection': PluginSchema,
    'httpapi': PluginSchema,
    'inventory': PluginSchema,
    'lookup': PluginSchema,
    'module': ModuleSchema,
    'netconf': PluginSchema,
    'shell': PluginSchema,
    'strategy': PluginSchema,
    'vars': PluginSchema,
}
