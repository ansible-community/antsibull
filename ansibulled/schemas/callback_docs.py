# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Schemas for the plugin DOCUMENTATION data."""

import typing as t

import pydantic as p

from .base import BaseModel, LocalConfig, transform_return_docs
from .plugin_docs import PluginDocSchema, PluginReturnSchema

REQUIRED_CALLBACK_TYPE_F = p.Field(..., regex='^(aggregate|notification|stdout)$')


class CallbackDocSchema(PluginDocSchema):
    type: str = REQUIRED_CALLBACK_TYPE_F


# Ignore Uninitialized attribute error as BaseModel works some magic to initialize the
# attributes when data is loaded into them.
# pyre-ignore[13]
class CallbackSchema(BaseModel):
    """Documentation of callback plugins."""

    class Config(LocalConfig):
        fields = {'return_': 'return',
                  }

    doc: CallbackDocSchema
    examples: str = ''
    metadata: t.Optional[t.Dict[str, t.Any]] = None
    return_: t.Dict[str, PluginReturnSchema] = {}

    @p.validator('return_', pre=True)
    def transform_return(cls, obj):
        return transform_return_docs(obj)

    @p.validator('examples', pre=True)
    def normalize_examples(cls, value):
        if value is None:
            value = ''
        return value
