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

from .base import (OPTION_TYPE_F, REQUIRED_ENV_VAR_F, RETURN_TYPE_F, COLLECTION_NAME_F, BaseModel,
                   DocSchema, JSONValueT, LocalConfig, OptionsSchema, list_from_scalars,
                   normalize_option_type_names, transform_return_docs)

_SENTINEL = object()


class OptionDeprecationSchema(BaseModel):
    """Schema for Option Deprecation Fields."""

    version: str = VERSION_F
    date: str = DATE_F
    collection_name: str = REQUIRED_COLLECTION_NAME_F
    why: str
    alternative: str = ''

    @p.root_validator(pre=True)
    def rename_version(cls, values):
        """Make deprecations at this level match the toplevel name."""
        removed_in = values.get('removed_in', _SENTINEL)
        if removed_in is not _SENTINEL:
            if values.get('version'):
                raise ValueError('Cannot specify `removed_in` if `version`'
                                 ' has been specified.')

            values['version'] = removed_in
            del values['removed_in']

        return values

    @p.root_validator(pre=True)
    def rename_date(cls, values):
        """Make deprecations at this level match the toplevel name."""
        removed_at_date = values.get('removed_at_date', _SENTINEL)
        if removed_at_date is not _SENTINEL:
            if values.get('date'):
                raise ValueError('Cannot specify `removed_at_date` if `date`'
                                 ' has been specified.')

            values['date'] = removed_at_date
            del values['removed_at_date']

        return values

    @p.root_validator(pre=True)
    def rename_collection_name(cls, values):
        """Make deprecations at this level match the toplevel name."""
        removed_from_collection = values.get('removed_from_collection', _SENTINEL)
        if removed_from_collection is not _SENTINEL:
            if values.get('collection_name'):
                raise ValueError('Cannot specify `removed_from_collection` if `collection_name`'
                                 ' has been specified.')

            values['collection_name'] = removed_from_collection
            del values['removed_from_collection']

        return values

    @p.root_validator(pre=True)
    def merge_typo_names(cls, values):
        alternatives = values.get('alternatives', _SENTINEL)

        if alternatives is not _SENTINEL:
            if values.get('alternative'):
                raise ValueError('Cannot specify `alternatives` if `alternative`'
                                 ' has been specified.')

            values['alternative'] = alternatives
            del values['alternatives']

        return values


class OptionEnvSchema(BaseModel):
    name: str = REQUIRED_ENV_VAR_F
    deprecated: OptionDeprecationSchema = p.Field({})
    version_added: str = 'historical'
    version_added_collection: str = COLLECTION_NAME_F


class OptionIniSchema(BaseModel):
    key: str
    section: str
    deprecated: OptionDeprecationSchema = p.Field({})
    version_added: str = 'historical'
    version_added_collection: str = COLLECTION_NAME_F


class OptionVarsSchema(BaseModel):
    name: str
    deprecated: OptionDeprecationSchema = p.Field({})
    version_added: str = 'historical'
    version_added_collection: str = COLLECTION_NAME_F


class ReturnSchema(BaseModel):
    """Schema of plugin return data docs."""

    description: t.List[str]
    choices: t.List[str] = []
    elements: str = OPTION_TYPE_F
    returned: str = 'success'
    sample: JSONValueT = ''
    type: str = RETURN_TYPE_F
    version_added: str = 'historical'
    version_added_collection: str = COLLECTION_NAME_F

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
    deprecated: OptionDeprecationSchema = p.Field({})


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
