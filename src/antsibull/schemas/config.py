# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2021
"""Schemas for config files."""

import os.path
import typing as t

import pydantic as p
import twiggy.formats
import twiggy.outputs

from .validators import convert_bool, convert_none, convert_path


#: Valid choices for a logging level field
LEVEL_CHOICES_F = p.Field(..., regex='^(CRITICAL|ERROR|WARNING|NOTICE|INFO|DEBUG|DISABLED)$')

#: Valid choices for a logging level field
DOC_PARSING_BACKEND_CHOICES_F = p.Field(
    'ansible-internal', regex='^(auto|ansible-doc|ansible-core-2.13|ansible-internal)$')

#: Valid choice of the logging version field
VERSION_CHOICES_F = p.Field(..., regex=r'1\.0')


#
# Configuration file schema
#

class BaseModel(p.BaseModel):
    class Config:
        allow_mutation = False
        extra = p.Extra.forbid
        validate_all = True


# pyre-ignore[13]: BaseModel initializes attributes when data is loaded
class LogFiltersModel(BaseModel):
    filter: t.Union[str, t.Callable]
    args: t.Sequence[t.Any] = []
    kwargs: t.Mapping[str, t.Any] = {}


# pyre-ignore[13]: BaseModel initializes attributes when data is loaded
class LogEmitterModel(BaseModel):
    output_name: str
    level: str = LEVEL_CHOICES_F
    filters: t.List[LogFiltersModel] = []


# pyre-ignore[13]: BaseModel initializes attributes when data is loaded
class LogOutputModel(BaseModel):
    output: t.Union[str, t.Callable]
    args: t.Sequence[t.Any] = []
    format: t.Union[str, t.Callable] = twiggy.formats.line_format
    kwargs: t.Mapping[str, t.Any] = {}

    @p.validator('args')
    # pylint:disable=no-self-argument,no-self-use
    def expand_home_dir_args(cls, args_field: t.MutableSequence,
                             values: t.Mapping) -> t.MutableSequence:
        """Expand tilde in the arguments of specific outputs."""
        if values['output'] in ('twiggy.outputs.FileOutput', twiggy.outputs.FileOutput):
            if args_field:
                args_field[0] = os.path.expanduser(args_field[0])
        return args_field

    @p.validator('kwargs')
    # pylint:disable=no-self-argument,no-self-use
    def expand_home_dir_kwargs(cls, kwargs_field: t.MutableMapping,
                               values: t.Mapping) -> t.MutableMapping:
        """Expand tilde in the keyword arguments of specific outputs."""
        if values['output'] in ('twiggy.outputs.FileOutput', twiggy.outputs.FileOutput):
            if 'name' in kwargs_field:
                kwargs_field['name'] = os.path.expanduser(kwargs_field['name'])
        return kwargs_field


class LoggingModel(BaseModel):
    emitters: t.Optional[t.Dict[str, LogEmitterModel]] = {}
    incremental: bool = False
    outputs: t.Optional[t.Dict[str, LogOutputModel]] = {}
    version: str = VERSION_CHOICES_F


#: Default logging configuration
DEFAULT_LOGGING_CONFIG = LoggingModel.parse_obj(
    {'version': '1.0',
     'outputs': {
         'logfile': {
             'output': 'twiggy.outputs.FileOutput',
             'args': [
                 '~/antsibull.log'
             ]
         },
         'stderr': {
             'output': 'twiggy.outputs.StreamOutput',
             'format': 'twiggy.formats.shell_format'
         },
     },
     'emitters': {
         'all': {
             'level': 'INFO',
             'output_name': 'logfile',
             'filters': []
         },
         'problems': {
             'level': 'WARNING',
             'output_name': 'stderr',
             'filters': []
         },
     }
     })


class ConfigModel(BaseModel):
    # pyre-ignore[8]: https://github.com/samuelcolvin/pydantic/issues/1684
    ansible_base_url: p.HttpUrl = 'https://github.com/ansible/ansible'
    breadcrumbs: p.StrictBool = True
    chunksize: int = 4096
    doc_parsing_backend: str = DOC_PARSING_BACKEND_CHOICES_F
    # pyre-ignore[8]: https://github.com/samuelcolvin/pydantic/issues/1684
    galaxy_url: p.HttpUrl = 'https://galaxy.ansible.com/'
    indexes: p.StrictBool = True
    logging_cfg: LoggingModel = DEFAULT_LOGGING_CONFIG
    max_retries: int = 10
    process_max: t.Optional[int] = None
    # pyre-ignore[8]: https://github.com/samuelcolvin/pydantic/issues/1684
    pypi_url: p.HttpUrl = 'https://pypi.org/'
    use_html_blobs: p.StrictBool = False
    thread_max: int = 8
    file_check_content: int = 262144
    collection_cache: t.Optional[str] = None

    _convert_nones = p.validator('process_max', pre=True, allow_reuse=True)(convert_none)
    _convert_bools = p.validator('breadcrumbs', 'indexes', 'use_html_blobs',
                                 pre=True, allow_reuse=True)(convert_bool)
    _convert_paths = p.validator('collection_cache',
                                 pre=True, allow_reuse=True)(convert_path)
