# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""General functions for working with aiohttp."""

import asyncio
import contextlib
import typing as t
import warnings

import aiohttp

from .. import app_context
from ..app_logging import log


mlog = log.fields(mod=__name__)


def _format_call(command: str, args: t.Tuple[t.Any, ...], kwargs: t.Mapping[str, t.Any]) -> str:
    arguments = [repr(a) for a in args] + ['{0}={1}'.format(k, repr(v)) for k, v in kwargs.items()]
    return 'aio_session.{command}({args})'.format(
        command=command,
        args=', '.join(arguments),
    )


@contextlib.asynccontextmanager
async def retry_get(aio_session: 'aiohttp.client.ClientSession',
                    *args,
                    acceptable_error_codes: t.Optional[t.Iterable[int]] = None,
                    max_retries: t.Optional[int] = None,
                    **kwargs) -> t.AsyncGenerator[aiohttp.ClientResponse, None]:
    flog = mlog.fields(func='retry_get')
    flog.debug('Enter')

    # Handle default value for max_retries
    lib_ctx = app_context.lib_ctx.get()
    if max_retries is None:
        max_retries = lib_ctx.max_retries

    # Make sure max_retries is at least 1
    max_retries = max(max_retries, 1)

    # Run HTTP requests
    call_string = _format_call('get', args, kwargs)
    try:
        error_codes = []
        for retry in range(max_retries):
            flog.debug('Execute {0}'.format(call_string))
            try:
                async with aio_session.get(*args, **kwargs) as response:
                    status_code = response.status
                    flog.debug('Status code {0}'.format(status_code))
                    if status_code < 400:
                        flog.debug('Yield')
                        yield response
                        return
                    if acceptable_error_codes is not None and status_code in acceptable_error_codes:
                        flog.debug('Yield')
                        yield response
                        return
                    error_codes.append(status_code)
            except Exception as error:
                flog.trace()
                status_code = str(error)
                error_codes.append(status_code)

            failed = retry + 1 == max_retries
            warnings.warn('{0} failed with status code {1}{2}'.format(
                call_string,
                status_code,
                ', finally failed.' if failed else ', retrying...'
            ))
            if failed:
                break

            await asyncio.sleep(retry * 0.5)

        flog.debug('Raise error')
        raise Exception('Repeated error when calling {0}: received status codes {1}'.format(
            call_string, ', '.join([str(error) for error in error_codes])))
    finally:
        flog.debug('Leave')
