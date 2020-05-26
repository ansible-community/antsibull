# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Schemas for the plugin DOCUMENTATION data."""

# Ignore Unitialized attribute errors because BaseModel works some magic
# to initialize the attributes when data is loaded into them.
# pyre-ignore-all-errors[13]

import typing as t

import pydantic as p

from .base import (OPTION_TYPE_F, REQUIRED_ENV_VAR_F, RETURN_TYPE_F, BaseModel, DeprecationSchema,
                   DocSchema, JSONValueT, LocalConfig, OptionsSchema, list_from_scalars,
                   normalize_option_type_names, transform_return_docs)

_SENTINEL = object()


class OptionEnvSchema(BaseModel):
    name: str = REQUIRED_ENV_VAR_F
    deprecated: DeprecationSchema = p.Field({})
    version_added: str = 'historical'


class OptionIniSchema(BaseModel):
    key: str
    section: str
    version_added: str = 'historical'


class OptionVarsSchema(BaseModel):
    name: str
    version_added: str = 'historical'


class ReturnSchema(BaseModel):
    """Schema of plugin return data docs."""

    description: t.List[str]
    choices: t.List[str] = []
    elements: str = OPTION_TYPE_F
    returned: str = 'success'
    sample: JSONValueT = ''
    type: str = RETURN_TYPE_F
    version_added: str = 'historical'

    @p.validator('description', pre=True)
    def list_from_scalars(cls, obj):
        return list_from_scalars(obj)

    @p.validator('type', 'elements', pre=True)
    def normalize_types(cls, obj):
        return normalize_option_type_names(obj)

    @p.root_validator(pre=True)
    def remove_example(cls, values):
        """
        Remove example in favor of sample.

        Having both sample and example is redundant.  Many more plugins are using sample so
        standardize on that.
        """
        example = values.get('example', _SENTINEL)

        if example is not _SENTINEL:
            if values.get('sample'):
                raise ValueError('Cannot specify `example` if `sample` has been specified.')

            values['sample'] = example
            del values['example']

        return values


class InnerReturnSchema(ReturnSchema):
    """Nested return schema which allows leaving out description."""

    contains: t.Dict[str, 'InnerReturnSchema'] = {}

    @p.root_validator(pre=True)
    def allow_description_to_be_optional(cls, values):
        # Doing this in a validator so that the json-schema will still flag it as an error
        if 'description' not in values:
            values['description'] = []
        return values


InnerReturnSchema.update_forward_refs()


class OuterReturnSchema(ReturnSchema):
    """Toplevel return schema."""

    contains: t.Dict[str, InnerReturnSchema] = {}


class PluginOptionsSchema(OptionsSchema):
    env: t.List[OptionEnvSchema] = []
    ini: t.List[OptionIniSchema] = []
    suboptions: t.Dict[str, 'PluginOptionsSchema'] = {}
    vars: t.List[OptionVarsSchema] = []


PluginOptionsSchema.update_forward_refs()


class InnerDocSchema(DocSchema):
    options: t.Dict[str, PluginOptionsSchema] = {}


class PluginDocSchema(BaseModel):
    doc: InnerDocSchema


class PluginExamplesSchema(BaseModel):
    examples: str = ''

    @p.validator('examples', pre=True)
    def normalize_examples(cls, value):
        if value is None:
            value = ''
        return value


class PluginMetadataSchema(BaseModel):
    metadata: t.Optional[t.Dict[str, t.Any]] = None


class PluginReturnSchema(BaseModel):
    class Config(LocalConfig):
        fields = {'return_': 'return',
                  }

    return_: t.Dict[str, OuterReturnSchema] = {}

    @p.validator('return_', pre=True)
    def transform_return(cls, obj):
        return transform_return_docs(obj)


class PluginSchema(PluginDocSchema, PluginExamplesSchema, PluginMetadataSchema, PluginReturnSchema,
                   BaseModel):
    """Documentation of an Ansible plugin."""
