# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Schemas for the plugin DOCUMENTATION data."""

import typing as t

import pydantic as p

from .base import BaseModel, DocSchema, OptionsSchema
from .plugin import PluginExamplesSchema, PluginMetadataSchema, PluginReturnSchema


class InnerModuleOptionsSchema(OptionsSchema):
    suboptions: t.Dict[str, 'InnerModuleOptionsSchema'] = {}

    @p.root_validator(pre=True)
    # pylint:disable=no-self-argument,no-self-use
    def allow_description_to_be_optional(cls, values):
        # Doing this in a validator so that the json-schema will still flag it as an error
        if 'description' not in values:
            values['description'] = []
        return values


InnerModuleOptionsSchema.update_forward_refs()


class ModuleOptionsSchema(OptionsSchema):
    suboptions: t.Dict[str, 'InnerModuleOptionsSchema'] = {}


class OuterModuleDocSchema(DocSchema):
    options: t.Dict[str, ModuleOptionsSchema] = {}
    has_action: bool = False


# Ignore Uninitialized attribute error as BaseModel works some magic to initialize the
# attributes when data is loaded into them.
# pyre-ignore[13]
class ModuleDocSchema(BaseModel):
    doc: OuterModuleDocSchema


class ModuleSchema(ModuleDocSchema, PluginExamplesSchema, PluginMetadataSchema,
                   PluginReturnSchema, BaseModel):
    """Documentation for modules."""
