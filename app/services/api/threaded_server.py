from __future__ import annotations

import socket
from threading import Thread
from time import sleep

import uvicorn

from app.services.api.asgi_app import static_web_app


class ThreadedUvicornServer:
    def __init__(self, host: str = '127.0.0.1', port: int = 56773) -> None:
        self.host = host
        self.port = port if port is not None else _find_free_port(host)
        self._thread: Thread | None = None
        self._server: uvicorn.Server | None = None

    @property
    def base_url(self) -> str:
        return f'http://{self.host}:{self.port}'

    def start(self, timeout_seconds: float = 3.0) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        config = uvicorn.Config(
            app=static_web_app,
            host=self.host,
            port=self.port,
            log_level='warning',
            access_log=False,
        )
        self._server = uvicorn.Server(config=config)
        self._thread = Thread(target=self._server.run, daemon=True)
        self._thread.start()

        waited = 0.0
        while not self._server.started and waited < timeout_seconds:
            sleep(0.05)
            waited += 0.05

        if not self._server.started:
            self.stop()
            raise RuntimeError('Local API server did not start in time.')

    def stop(self, timeout_seconds: float = 3.0) -> None:
        if self._server is not None:
            self._server.should_exit = True

        if self._thread is not None:
            self._thread.join(timeout=timeout_seconds)

        self._thread = None
        self._server = None


def _find_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_:
        socket_.bind((host, 0))
        return int(socket_.getsockname()[1])
