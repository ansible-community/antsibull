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

from .base import (REQUIRED_CLI_F, REQUIRED_ENV_VAR_F, RETURN_TYPE_F,
                   COLLECTION_NAME_F, BaseModel, DeprecationSchema, DocSchema,
                   LocalConfig, OptionsSchema, list_from_scalars, is_json_value,
                   normalize_return_type_names, transform_return_docs)

_SENTINEL = object()


class OptionCliSchema(BaseModel):
    name: str = REQUIRED_CLI_F
    deprecated: DeprecationSchema = p.Field({})
    option: str = ''
    version_added: str = 'historical'
    version_added_collection: str = COLLECTION_NAME_F

    @p.root_validator(pre=True)
    # pylint:disable=no-self-argument,no-self-use
    def add_option(cls, values):
        """
        Add option if not present
        """
        option = values.get('option', _SENTINEL)

        if option is _SENTINEL:
            values['option'] = f'--{values["name"].replace("_", "-")}'

        return values


class OptionEnvSchema(BaseModel):
    name: str = REQUIRED_ENV_VAR_F
    deprecated: DeprecationSchema = p.Field({})
    version_added: str = 'historical'
    version_added_collection: str = COLLECTION_NAME_F


class OptionIniSchema(BaseModel):
    key: str
    section: str
    deprecated: DeprecationSchema = p.Field({})
    version_added: str = 'historical'
    version_added_collection: str = COLLECTION_NAME_F


class OptionVarsSchema(BaseModel):
    name: str
    deprecated: DeprecationSchema = p.Field({})
    version_added: str = 'historical'
    version_added_collection: str = COLLECTION_NAME_F


class OptionKeywordSchema(BaseModel):
    name: str
    deprecated: DeprecationSchema = p.Field({})
    version_added: str = 'historical'
    version_added_collection: str = COLLECTION_NAME_F


class ReturnSchema(BaseModel):
    """Schema of plugin return data docs."""

    description: t.List[str]
    choices: t.List[str] = []
    elements: str = RETURN_TYPE_F
    returned: str = 'success'
    sample: t.Any = None  # JSON value
    type: str = RETURN_TYPE_F
    version_added: str = 'historical'
    version_added_collection: str = COLLECTION_NAME_F

    @p.validator('description', pre=True)
    # pylint:disable=no-self-argument,no-self-use
    def list_from_scalars(cls, obj):
        return list_from_scalars(obj)

    @p.validator('sample', pre=True)
    # pylint:disable=no-self-argument,no-self-use
    def is_json_value(cls, obj):
        if not is_json_value(obj):
            raise ValueError('`sample` must be a JSON value')
        return obj

    @p.validator('type', 'elements', pre=True)
    # pylint:disable=no-self-argument,no-self-use
    def normalize_types(cls, obj):
        return normalize_return_type_names(obj)

    @p.root_validator(pre=True)
    # pylint:disable=no-self-argument,no-self-use
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

            if not is_json_value(example):
                raise ValueError('`example` must be a JSON value')

            values['sample'] = example
            del values['example']

        return values


class InnerReturnSchema(ReturnSchema):
    """Nested return schema which allows leaving out description."""

    contains: t.Dict[str, 'InnerReturnSchema'] = {}

    @p.root_validator(pre=True)
    # pylint:disable=no-self-argument,no-self-use
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
    cli: t.List[OptionCliSchema] = []
    env: t.List[OptionEnvSchema] = []
    ini: t.List[OptionIniSchema] = []
    suboptions: t.Dict[str, 'PluginOptionsSchema'] = {}
    vars: t.List[OptionVarsSchema] = []
    keyword: t.List[OptionKeywordSchema] = []
    deprecated: DeprecationSchema = p.Field({})


PluginOptionsSchema.update_forward_refs()


class InnerDocSchema(DocSchema):
    options: t.Dict[str, PluginOptionsSchema] = {}


class PluginDocSchema(BaseModel):
    doc: InnerDocSchema


class PluginExamplesSchema(BaseModel):
    examples: str = ''

    @p.validator('examples', pre=True)
    # pylint:disable=no-self-argument,no-self-use
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
    # pylint:disable=no-self-argument,no-self-use
    def transform_return(cls, obj):
        return transform_return_docs(obj)


class PluginSchema(PluginDocSchema, PluginExamplesSchema, PluginMetadataSchema, PluginReturnSchema,
                   BaseModel):
    """Documentation of an Ansible plugin."""
