from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.services.api import ThreadedUvicornServer

IncomingMapMessageHandler = Callable[[int, dict[str, Any]], None]


class MapService:
    def __init__(self) -> None:
        self._server = ThreadedUvicornServer()

    @property
    def map_url(self) -> str:
        return f'{self._server.base_url}/index.html'

    def start(self) -> None:
        self._server.start()

    def stop(self) -> None:
        self._server.stop()

    def send_json(self, payload: dict[str, Any], timeout_seconds: float = 1.0) -> int:
        return self._server.send_json(payload=payload, timeout_seconds=timeout_seconds)

    def send_cmd(
        self,
        command: str,
        data: dict[str, Any] | None = None,
        timeout_seconds: float = 1.0,
    ) -> int:
        payload: dict[str, Any] = {
            'type': 'cmd',
            'command': command,
            'data': data or {},
        }
        return self.send_json(payload=payload, timeout_seconds=timeout_seconds)

    def set_web_message_handler(
        self, handler: IncomingMapMessageHandler | None
    ) -> None:
        self._server.set_web_message_handler(handler)
