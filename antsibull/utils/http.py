# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""General functions for working with aiohttp."""

import asyncio
import typing as t
import warnings

import aiohttp

from .. import app_context
from ..logging import log


mlog = log.fields(mod=__name__)


def _format_call(command: str, args: t.Tuple[t.Any, ...], kwargs: t.Mapping[str, t.Any]) -> str:
    arguments = [repr(a) for a in args] + ['{0}={1}'.format(k, repr(v)) for k, v in kwargs.items()]
    return 'aio_session.{command}({args})'.format(
        command=command,
        args=', '.join(arguments),
    )


class RetryGetManager:
    response: t.Optional[aiohttp.ClientResponse]

    def __init__(self,
                 aio_session: 'aiohttp.client.ClientSession',
                 args: t.Tuple[t.Any, ...],
                 kwargs: t.Mapping[str, t.Any],
                 max_retries: int,
                 acceptable_error_codes: t.Iterable[int],
                 ):
        self.aio_session = aio_session
        self.args = args
        self.kwargs = kwargs
        self.max_retries = max_retries
        self.acceptable_error_codes = acceptable_error_codes
        self.call_string = _format_call('get', args, kwargs)
        self.response = None

    async def __aenter__(self) -> aiohttp.ClientResponse:
        flog = mlog.fields(func='RetryGetManager.__aenter__')
        flog.debug('Enter')

        error_codes = []
        for retry in range(self.max_retries):
            flog.debug('Execute {0}', self.call_string)
            try:
                response = await self.aio_session.get(*self.args, **self.kwargs)
                status_code = response.status
                flog.debug('Status code {0}'.format(status_code))
                if status_code < 400 or status_code in self.acceptable_error_codes:
                    self.response = response
                    flog.debug('Leave')
                    return response
                error_codes.append(status_code)
                response.close()
            except Exception as error:
                flog.trace()
                status_code = str(error)
                error_codes.append(status_code)

            failed = retry + 1 == self.max_retries
            warnings.warn('{0} failed with status code {1}{2}'.format(
                self.call_string,
                status_code,
                ', finally failed.' if failed else ', retrying...'
            ))
            if failed:
                break

            await asyncio.sleep(retry * 0.5)

        flog.debug('Raise error')
        raise Exception('Repeated error when calling {0}: received status codes {1}'.format(
            self.call_string, ', '.join([str(error) for error in error_codes])))

    async def __aexit__(self, exc_type, exc, tb) -> None:
        flog = mlog.fields(func='RetryGetManager.__aexit__')
        flog.debug('Enter')
        response = self.response
        self.response = None
        if response is not None:
            response.close()
        flog.debug('Leave')


def retry_get(aio_session: 'aiohttp.client.ClientSession',
              *args,
              acceptable_error_codes: t.Optional[t.Iterable[int]] = None,
              max_retries: t.Optional[int] = None,
              **kwargs) -> t.AsyncContextManager[aiohttp.ClientResponse]:
    # Handle default value for max_retries
    lib_ctx = app_context.lib_ctx.get()
    if max_retries is None:
        max_retries = lib_ctx.max_retries

    # Make sure max_retries is at least 1
    max_retries = max(max_retries, 1)

    # pyre-ignore[7]: no idea how to make pyre see that RetryGetManager has correct type
    return RetryGetManager(aio_session, args, kwargs, max_retries, acceptable_error_codes or ())
