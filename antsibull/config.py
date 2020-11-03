# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functions to handle config files."""

import itertools
import os.path
import typing as t

import perky
import pydantic as p
import twiggy.formats
import twiggy.outputs

from .logging import log


mlog = log.fields(mod=__name__)

#: Valid choices for a logging level field
LEVEL_CHOICES_F = p.Field(..., regex='^(CRITICAL|ERROR|WARNING|NOTICE|INFO|DEBUG|DISABLED)$')

#: Valid choices for a logging level field
DOC_PARSING_BACKEND_CHOICES_F = p.Field(
    'ansible-internal', regex='^(ansible-doc|ansible-internal)$')

#: Valid choice of the logging version field
VERSION_CHOICES_F = p.Field(..., regex=r'1\.0')

#: System config file location.
SYSTEM_CONFIG_FILE = '/etc/antsibull.cfg'

#: Per-user config file location.
USER_CONFIG_FILE = '~/.antsibull.cfg'


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
    def expand_home_dir_args(cls, args_field: t.MutableSequence,
                             values: t.Mapping) -> t.MutableSequence:
        """Expand tilde in the arguments of specific outputs."""
        if values['output'] in ('twiggy.outputs.FileOutput', twiggy.outputs.FileOutput):
            if args_field:
                args_field[0] = os.path.expanduser(args_field[0])
        return args_field

    @p.validator('kwargs')
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
    chunksize: int = 4096
    # pyre-ignore[8]: https://github.com/samuelcolvin/pydantic/issues/1684
    galaxy_url: p.HttpUrl = 'https://galaxy.ansible.com/'
    logging_cfg: LoggingModel = DEFAULT_LOGGING_CONFIG
    process_max: t.Optional[int] = None
    # pyre-ignore[8]: https://github.com/samuelcolvin/pydantic/issues/1684
    pypi_url: p.HttpUrl = 'https://pypi.org/'
    thread_max: int = 80
    max_retries: int = 10
    doc_parsing_backend: str = DOC_PARSING_BACKEND_CHOICES_F

    @p.validator('process_max', pre=True)
    def convert_to_none(cls, value):
        if value is None:
            # Default is already None
            return None
        if value.lower() in ('none', 'null'):
            value = None
        return value


def find_config_files(conf_files: t.Iterable[str]) -> t.List[str]:
    """
    Find all config files that exist.

    :arg conf_files: An iterable of config filenames to search for.
    :returns: A List of filenames which actually existed on the system.
    """
    flog = mlog.fields(func='find_config_file')
    flog.fields(conf_files=conf_files).debug('Enter')

    paths = [os.path.abspath(p) for p in conf_files]
    flog.fields(paths=paths).info('Paths to check')

    config_files = []
    for conf_path in paths:
        if os.path.exists(conf_path):
            config_files.append(conf_path)
    flog.fields(paths=config_files).info('Paths found')

    flog.debug('Leave')
    return config_files


def read_config(filename: str) -> ConfigModel:
    """
    Parse a config file and return the data from it.

    :arg filename: The filename of the config file to parse.
    :returns: A ConfigModel model containing the config data.
    """
    flog = mlog.fields(func='read_config')
    flog.debug('Enter')

    filename = os.path.abspath(filename)

    flog.fields(filename=filename).info('loading config file')
    raw_config_data = perky.load(filename)
    flog.debug('Validatinging the config file data')
    # Note: We parse the object but discard the model because we want to validate the config but let
    # the context handle all setting of defaults
    ConfigModel.parse_obj(raw_config_data)

    flog.debug('Leave')
    return raw_config_data


def load_config(conf_files: t.Union[t.Iterable[str], str, None] = None) -> t.Dict:
    """
    Load configuration.

    Load configuration from all found conf files.  The default configuration is loaded
    followed by a system-wide location, user-location, and then any files specified in
    the ``conf_files`` parameter.  Toplevel keys in later files will overwrite earlier
    those same keys in earlier files.

    :arg conf_files: An iterable of conf_files to load configuration information from.
    :returns: A dict containing the configuration.
    """
    flog = mlog.fields(func='load_config')
    flog.debug('Enter')

    if isinstance(conf_files, str):
        conf_files = (conf_files,)
    elif conf_files is None:
        conf_files = ()

    user_config_file = os.path.expanduser(USER_CONFIG_FILE)
    available_files = find_config_files(itertools.chain((SYSTEM_CONFIG_FILE, user_config_file),
                                                        conf_files))

    includes = list(available_files)

    flog.debug('loading config files')
    # Perky has some bugs that prevent this simple way from working:
    # https://github.com/ansible-community/antsibull/pull/118
    # cfg = {'includes': includes}
    # cfg = perky.includes(cfg, recursive=True)

    # Workaround for above bug.  Note that includes specified in the config files will not work
    # but we can just add that as a new feature when perky gets it working.
    cfg = {}
    for filename in includes:
        new_cfg = perky.load(filename)
        cfg.update(new_cfg)

    flog.debug('validating configuration')
    # Note: We parse the object but discard the model because we want to validate the config but let
    # the context handle all setting of defaults
    ConfigModel.parse_obj(cfg)

    flog.fields(config=cfg).debug('Leave')
    return cfg
