from __future__ import annotations

from collections.abc import Callable
from typing import Any

import polars as pl

from app.constants.data_schema import SCHEMA
from app.services.api import ThreadedUvicornServer
from app.utils.target_color import target_color_hex

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

    def focus_target(self, target_id: str, latitude: float, longitude: float) -> None:
        """Focus/center map on a specific target.
        
        Args:
            target_id: The target ID to focus on
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            The command ID
        """
        data = {
            'target_id': target_id,
            'latitude': latitude,
            'longitude': longitude,
        }
        self.send_cmd(command='focus_target', data=data)

    def set_web_message_handler(
        self, handler: IncomingMapMessageHandler | None
    ) -> None:
        self._server.set_web_message_handler(handler)

    def update_targets(self, df: pl.DataFrame) -> None:
        """Convert polars DataFrame to GeoJSON and send to web clients.
        
        Args:
            df: DataFrame with columns: target_id, target_name, type, datetime,
                latitude, longitude, height, speed
        """
        if df.is_empty():
            geojson: dict[str, Any] = {'type': 'FeatureCollection', 'features': []}
        else:
            records = df.to_dicts()
            
            features = []
            for record in records:
                dt_value = record.get(SCHEMA.DATETIME)
                datetime_str = dt_value.isoformat() if dt_value is not None else None
                
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [
                            record.get(SCHEMA.LONGITUDE),
                            record.get(SCHEMA.LATITUDE),
                        ],
                    },
                    'properties': {
                        'target_id': record.get(SCHEMA.TARGET_ID),
                        'target_name': record.get(SCHEMA.TARGET_NAME),
                        'type': record.get(SCHEMA.TYPE),
                        'color': target_color_hex(record.get(SCHEMA.TARGET_ID)),
                        'datetime': datetime_str,
                        'height': record.get(SCHEMA.HEIGHT),
                        'speed': record.get(SCHEMA.SPEED),
                    },
                }
                features.append(feature)
            
            geojson = {'type': 'FeatureCollection', 'features': features}
        
        self.send_cmd(command='update_targets', data=geojson)
