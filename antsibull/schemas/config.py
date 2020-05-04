# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Models for the antsibull config file."""

# Ignore Unitialized attribute errors because BaseModel works some magic
# to initialize the attributes when data is loaded into them.
# pyre-ignore-all-errors[13]


import typing as t

import pydantic as p
import twiggy.formats
import twiggy.outputs


LEVEL_CHOICES_F = p.Field(..., regex='^(CRITICAL|ERROR|WARNING|NOTICE|INFO|DEBUG|DISABLED)$')
VERSION_CHOICES_F = p.Field(..., regex=r'1\.0')


class FiltersSchema(p.BaseModel):
    filter: t.Union[str, t.Callable]
    args: t.Sequence[t.Any] = []
    kwargs: t.Mapping[str, t.Any] = {}


class EmitterSchema(p.BaseModel):
    level: str = LEVEL_CHOICES_F
    output_name: str
    filters: t.Optional[FiltersSchema] = None


class OutputSchema(p.BaseModel):
    output: t.Union[str, t.Callable]
    args: t.Sequence[t.Any] = []
    format: t.Union[str, t.Callable] = twiggy.formats.line_format
    kwargs: t.Mapping[str, t.Any] = {}


class ConfigSchema(p.BaseModel):
    emitters: t.Optional[t.Dict[str, EmitterSchema]] = {}
    incremental: bool = False
    outputs: t.Optional[t.Dict[str, OutputSchema]] = {}
    version: str = VERSION_CHOICES_F
