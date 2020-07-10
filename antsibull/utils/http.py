# Author: Felix Fontein <felix@fontein.de>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""General functions for working with aiohttp."""

import asyncio
import typing as t

import aiohttp


def _format_call(command: str, args: t.Tuple[t.Any, ...], kwargs: t.Mapping[str, t.Any]) -> str:
    arguments = [repr(a) for a in args] + ['{0}={1}'.format(k, repr(v)) for k, v in kwargs.items()]
    return 'aio_session.{command}({args})'.format(
        command=command,
        args=', '.join(arguments),
    )


async def retry_get(aio_session: 'aiohttp.client.ClientSession',
                    *args,
                    acceptable_error_codes: t.Optional[t.Iterable[int]] = None,
                    max_retries: int = 10,
                    **kwargs) -> None:
    error_codes = []
    for retry in range(max_retries):
        response = await aio_session.get(*args, **kwargs)

        status_code = response.status
        if status_code < 400:
            return response
        if acceptable_error_codes is not None and status_code in acceptable_error_codes:
            return response
        response.close()

        error_codes.append(status_code)

        failed = retry + 1 == max_retries
        print('{0}: {1} failed with status code {2}{3}'.format(
            'ERROR' if failed else 'WARNING',
            _format_call('get', args, kwargs),
            status_code,
            ', finally failed.' if failed else ', retrying...'
        ))

        await asyncio.sleep(retry * 0.5)

    raise Exception('Repeated error when calling {0}: received status codes {1}'.format(
        _format_call('get', args, kwargs), ', '.join([str(error) for error in error_codes])))
