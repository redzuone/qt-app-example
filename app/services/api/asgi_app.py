from __future__ import annotations

import mimetypes
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import unquote

WEB_ROOT = Path(__file__).resolve().parents[2] / 'web'
Scope = Mapping[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


async def static_web_app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope['type'] != 'http':
        return

    method = scope['method']
    if method not in {'GET', 'HEAD'}:
        await send(
            {
                'type': 'http.response.start',
                'status': 405,
                'headers': [(b'content-type', b'text/plain; charset=utf-8')],
            }
        )
        await send({'type': 'http.response.body', 'body': b'Method Not Allowed'})
        return

    raw_path = unquote(scope.get('path', '/'))
    relative_path = raw_path.lstrip('/') or 'index.html'
    requested_path = (WEB_ROOT / relative_path).resolve()

    if WEB_ROOT not in requested_path.parents and requested_path != WEB_ROOT:
        await _send_not_found(send)
        return

    if requested_path.is_dir():
        requested_path = requested_path / 'index.html'

    if not requested_path.exists() or not requested_path.is_file():
        await _send_not_found(send)
        return

    content_type, _ = mimetypes.guess_type(str(requested_path))
    headers = [(b'content-type', (content_type or 'application/octet-stream').encode('utf-8'))]

    await send({'type': 'http.response.start', 'status': 200, 'headers': headers})
    if method == 'HEAD':
        await send({'type': 'http.response.body', 'body': b''})
        return

    body = requested_path.read_bytes()
    await send({'type': 'http.response.body', 'body': body})


async def _send_not_found(send: Send) -> None:
    await send(
        {
            'type': 'http.response.start',
            'status': 404,
            'headers': [(b'content-type', b'text/plain; charset=utf-8')],
        }
    )
    await send({'type': 'http.response.body', 'body': b'Not Found'})
