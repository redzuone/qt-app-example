from __future__ import annotations

from app.services.api import ThreadedUvicornServer


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
