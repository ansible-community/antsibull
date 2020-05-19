# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Schemas for the plugin DOCUMENTATION data."""

import typing as t

import pydantic as p

from .base import (BaseModel, DocSchema, LocalConfig, OptionsSchema, transform_return_docs)
from .plugin_docs import PluginReturnSchema


class InnerModuleOptionsSchema(OptionsSchema):
    suboptions: t.Dict[str, 'InnerModuleOptionsSchema'] = {}

    @p.root_validator(pre=True)
    def allow_description_to_be_optional(cls, values):
        # Doing this in a validator so that the json-schema will still flag it as an error
        if 'description' not in values:
            values['description'] = []
        return values


InnerModuleOptionsSchema.update_forward_refs()


class ModuleOptionsSchema(OptionsSchema):
    suboptions: t.Dict[str, 'InnerModuleOptionsSchema'] = {}


class ModuleDocSchema(DocSchema):
    options: t.Dict[str, ModuleOptionsSchema] = {}


# Ignore Uninitialized attribute error as BaseModel works some magic to initialize the
# attributes when data is loaded into them.
# pyre-ignore[13]
class ModuleSchema(BaseModel):
    """Documentation for modules."""

    class Config(LocalConfig):
        fields = {'return_': 'return',
                  }

    doc: ModuleDocSchema
    examples: str = ''
    metadata: t.Optional[t.Dict[str, t.Any]] = None
    # return_: t.Dict[str, t.Any] = {}
    return_: t.Dict[str, PluginReturnSchema] = {}

    @p.validator('return_', pre=True)
    def transform_return(cls, obj):
        return transform_return_docs(obj)

    @p.validator('examples', pre=True)
    def normalize_examples(cls, value):
        if value is None:
            value = ''
        return value
