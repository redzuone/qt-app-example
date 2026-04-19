from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
from collections.abc import Awaitable, Callable, Mapping
from itertools import count
from pathlib import Path
from threading import Lock
from time import time
from typing import Any
from urllib.parse import unquote

WEB_ROOT = Path(__file__).resolve().parents[2] / 'web'
Scope = Mapping[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
IncomingMessageHandler = Callable[[int, dict[str, Any]], None]

HELLO_INTERVAL_SECONDS = 2.0
HELLO_REPLY_TIMEOUT_SECONDS = 6.0
HELLO_REPLY_CHECK_INTERVAL_SECONDS = 1.0

logger = logging.getLogger(__name__)
_next_connection_id = count(1)
_websocket_connections: dict[int, Send] = {}
_websocket_connections_lock = Lock()
_incoming_message_handler: IncomingMessageHandler | None = None


def set_incoming_message_handler(handler: IncomingMessageHandler | None) -> None:
    global _incoming_message_handler
    _incoming_message_handler = handler


async def broadcast_json(payload: Mapping[str, Any]) -> int:
    message_text = json.dumps(dict(payload))

    with _websocket_connections_lock:
        active_connections = list(_websocket_connections.items())

    delivered_count = 0
    for connection_id, connection_send in active_connections:
        try:
            await connection_send({'type': 'websocket.send', 'text': message_text})
            delivered_count += 1
        except Exception:
            logger.warning(
                'Failed to send websocket message to connection %s.', connection_id
            )

    return delivered_count


async def send_json_to_connection(
    connection_id: int, payload: Mapping[str, Any]
) -> int:
    message_text = json.dumps(dict(payload))

    with _websocket_connections_lock:
        connection_send = _websocket_connections.get(connection_id)

    if connection_send is None:
        return 0

    try:
        await connection_send({'type': 'websocket.send', 'text': message_text})
        return 1
    except Exception:
        logger.warning(
            'Failed to send websocket message to connection %s.', connection_id
        )
        return 0


async def static_web_app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope['type'] == 'websocket' and scope.get('path') == '/ws':
        await _websocket_hello_app(receive, send)
        return

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
    headers = [
        (b'content-type', (content_type or 'application/octet-stream').encode('utf-8'))
    ]

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


async def _websocket_hello_app(receive: Receive, send: Send) -> None:
    await send({'type': 'websocket.accept'})

    connection_id = next(_next_connection_id)
    await _register_connection(connection_id, send)
    _dispatch_incoming_message(connection_id, {'type': 'websocket_connected'})

    connection_state = {'last_reply_at': time(), 'timeout_logged': False}
    hello_task = asyncio.create_task(_send_hello_interval(send))
    reply_watchdog_task = asyncio.create_task(
        _watch_missing_reply(send, connection_state)
    )
    try:
        while True:
            message = await receive()
            message_type = message.get('type')

            if message_type == 'websocket.disconnect':
                logger.info('WebSocket client %s disconnected.', connection_id)
                break

            if message_type != 'websocket.receive':
                continue

            payload = message.get('text')
            if not payload:
                continue

            parsed_message = _consume_client_message(payload)
            if parsed_message is None:
                continue

            client_message_type = parsed_message.get('type')
            if client_message_type == 'hello_reply':
                connection_state['last_reply_at'] = time()
                connection_state['timeout_logged'] = False
                continue

            _dispatch_incoming_message(connection_id, parsed_message)
    finally:
        hello_task.cancel()
        reply_watchdog_task.cancel()
        await asyncio.gather(hello_task, reply_watchdog_task, return_exceptions=True)
        await _unregister_connection(connection_id)


async def _send_hello_interval(send: Send) -> None:
    while True:
        payload = {
            'type': 'hello',
            'timestamp': time(),
        }
        await send({'type': 'websocket.send', 'text': json.dumps(payload)})
        await asyncio.sleep(HELLO_INTERVAL_SECONDS)


async def _watch_missing_reply(
    send: Send, connection_state: dict[str, float | bool]
) -> None:
    while True:
        elapsed_seconds = time() - float(connection_state['last_reply_at'])
        if elapsed_seconds > HELLO_REPLY_TIMEOUT_SECONDS:
            if not bool(connection_state['timeout_logged']):
                logger.warning(
                    'WebSocket hello_reply missing for %.1fs; closing stale connection.',
                    elapsed_seconds,
                )
                connection_state['timeout_logged'] = True

            await send(
                {
                    'type': 'websocket.close',
                    'code': 1011,
                    'reason': 'hello_reply timeout',
                }
            )
            return

        await asyncio.sleep(HELLO_REPLY_CHECK_INTERVAL_SECONDS)


async def _register_connection(connection_id: int, send: Send) -> None:
    with _websocket_connections_lock:
        _websocket_connections[connection_id] = send
        logger.info('WebSocket client %s connected.', connection_id)


async def _unregister_connection(connection_id: int) -> None:
    with _websocket_connections_lock:
        _websocket_connections.pop(connection_id, None)
        logger.info('WebSocket client %s disconnected.', connection_id)


def _dispatch_incoming_message(connection_id: int, message: dict[str, Any]) -> None:
    if _incoming_message_handler is None:
        return

    try:
        _incoming_message_handler(connection_id, message)
    except Exception:
        logger.exception(
            'Incoming websocket message handler failed for connection %s.',
            connection_id,
        )


def _consume_client_message(payload: str) -> dict[str, Any] | None:
    try:
        message = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(message, dict):
        return None

    if not isinstance(message.get('type'), str):
        return None

    return message
