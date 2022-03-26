# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Toshio Kuratomi, 2021
"""Schemas for app and lib contexts."""

import typing as t

import pydantic as p

from .config import DEFAULT_LOGGING_CONFIG, LoggingModel
from .validators import convert_bool, convert_none, convert_path
from ..utils.collections import ContextDict


class BaseModel(p.BaseModel):
    """
    Configuration for all Context object classes.

    :cvar Config: Sets the following information

        :cvar allow_mutation: ``False``.  Prevents setattr on the contexts.
        :cvar extra: ``p.Extra.forbid``.  Prevents extra fields on the contexts.
        :cvar validate_all: ``True``.  Validates default values as well as user supplied ones.
    """

    class Config:
        """
        Set default configuration for building the context models.

        :cvar allow_mutation: ``False``.  Prevents setattr on the contexts.
        :cvar extra: ``p.Extra.forbid``.  Prevents extra fields on the contexts.
        :cvar validate_all: ``True``.  Validates default values as well as user supplied ones.
        """

        allow_mutation = False
        extra = p.Extra.forbid
        validate_all = True


class AppContext(BaseModel):
    """
    Structure and defaults of the app_ctx.

    :ivar extra: a mapping of arg/config keys to values.  Anything in here is unchecked by a
        schema.  These are usually leftover command line arguments and config entries. If
        values stored in extras need default values, they need to be set outside of the context
        or the entries can be given an actual entry in the AppContext to take advantage of the
        schema's checking, normalization, and default setting.
    :ivar ansible_base_url: Url to the ansible-core git repo.
    :ivar breadcrumbs: If True, build with breadcrumbs on the plugin pages (this takes more memory).
    :ivar use_html_blobs: If True, use HTML blobs instead of RST tables for option and return value
        tables (this takes less memory).
    :ivar galaxy_url: URL of the galaxy server to get collection info from
    :ivar indexes: If True, create index pages for all collections and all plugins in a collection.
    :ivar logging_cfg: Configuration of the application logging
    :ivar pypi_url: URL of the pypi server to query for information
    :ivar collection_cache: If set, must be a path pointing to a directory where collection
        tarballs are cached so they do not need to be downloaded from Galaxy twice.
    """

    extra: ContextDict = ContextDict()
    # pyre-ignore[8]: https://github.com/samuelcolvin/pydantic/issues/1684
    ansible_base_url: p.HttpUrl = 'https://github.com/ansible/ansible/'
    breadcrumbs: p.StrictBool = True
    # pyre-ignore[8]: https://github.com/samuelcolvin/pydantic/issues/1684
    galaxy_url: p.HttpUrl = 'https://galaxy.ansible.com/'
    indexes: p.StrictBool = True
    logging_cfg: LoggingModel = LoggingModel.parse_obj(DEFAULT_LOGGING_CONFIG)
    # pyre-ignore[8]: https://github.com/samuelcolvin/pydantic/issues/1684
    pypi_url: p.HttpUrl = 'https://pypi.org/'
    use_html_blobs: p.StrictBool = False
    collection_cache: t.Optional[str] = None

    _convert_bools = p.validator('breadcrumbs', 'indexes', 'use_html_blobs',
                                 pre=True, allow_reuse=True)(convert_bool)
    _convert_paths = p.validator('collection_cache',
                                 pre=True, allow_reuse=True)(convert_path)


class LibContext(BaseModel):
    """
    Structure and defaults of the lib_ctx.

    :ivar chunksize: number of bytes to read or write at one time for network or file IO
    :ivar process_max: Maximum number of worker processes for parallel operations.  It may be None
        to mean, use all available CPU cores.
    :ivar thread_max: Maximum number of helper threads for parallel operations
    :ivar file_check_content: Maximum number of bytes of a file to read before writing it to
        compare contents. If contents are as expected, file is not overwritten. Set to 0 to
        disable.
    :ivar max_retries: Maximum number of times to retry an http request (in case of timeouts and
        other transient problems.
    :ivar doc_parsing_backend: The backend to use for parsing the documentation strings from
        plugins.  'auto' selects a backend depending on the ansible-core version.
        'ansible-internal' is the fastest, but does not work with ansible-core 2.13+.
        'ansible-core-2.13' is also very fast, but requires ansible-core 2.13+.
        'ansible-doc' exists in case of problems with the ansible-internal backend.
    """

    chunksize: int = 4096
    doc_parsing_backend: str = 'auto'
    max_retries: int = 10
    process_max: t.Optional[int] = None
    thread_max: int = 8
    file_check_content: int = 262144

    _convert_nones = p.validator('process_max', pre=True, allow_reuse=True)(convert_none)
