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
    def base_url(self) -> str:
        return f'{self._server.base_url}'

    @property
    def map_url(self) -> str:
        return f'{self._server.base_url}/maplibre'

    def start(self) -> None:
        self._server.start()

    def stop(self) -> None:
        self._server.stop()

    def send_json(self, payload: dict[str, Any], timeout_seconds: float = 1.0) -> int:
        return self._server.send_json(payload=payload, timeout_seconds=timeout_seconds)

    def send_json_to_connection(
        self,
        connection_id: int,
        payload: dict[str, Any],
        timeout_seconds: float = 1.0,
    ) -> int:
        return self._server.send_json_to_connection(
            connection_id=connection_id,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )

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

    def send_cmd_to_connection(
        self,
        connection_id: int,
        command: str,
        data: dict[str, Any] | None = None,
        timeout_seconds: float = 1.0,
    ) -> int:
        payload: dict[str, Any] = {
            'type': 'cmd',
            'command': command,
            'data': data or {},
        }
        return self.send_json_to_connection(
            connection_id=connection_id,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )

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

    def set_sensor_center(
        self,
        latitude: float,
        longitude: float,
        connection_id: int | None = None,
        fit: bool = False,
    ) -> None:
        data = {
            'latitude': latitude,
            'longitude': longitude,
            'fit': fit,
        }

        if connection_id is None:
            self.send_cmd(command='set_sensor_center', data=data)
            return

        self.send_cmd_to_connection(
            connection_id=connection_id,
            command='set_sensor_center',
            data=data,
        )

    def set_map_brightness(
        self,
        brightness: float,
        connection_id: int | None = None,
    ) -> None:
        data = {
            'brightness': brightness,
        }

        if connection_id is None:
            self.send_cmd(command='set_map_brightness', data=data)
            return

        self.send_cmd_to_connection(
            connection_id=connection_id,
            command='set_map_brightness',
            data=data,
        )

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

    def update_trails(self, df: pl.DataFrame, fade_segments: bool = True) -> None:
        """Convert per-point DataFrame to per-target trail GeoJSON."""
        if df.is_empty():
            geojson: dict[str, Any] = {'type': 'FeatureCollection', 'features': []}
            self.send_cmd(command='update_trails', data=geojson)
            return

        records = df.sort([SCHEMA.TARGET_ID, SCHEMA.DATETIME]).to_dicts()
        target_points: dict[str, list[list[float]]] = {}
        target_props: dict[str, dict[str, Any]] = {}

        for record in records:
            target_id = record.get(SCHEMA.TARGET_ID)
            latitude = record.get(SCHEMA.LATITUDE)
            longitude = record.get(SCHEMA.LONGITUDE)
            if target_id is None or latitude is None or longitude is None:
                continue

            target_id_str = str(target_id)
            target_points.setdefault(target_id_str, []).append([longitude, latitude])
            target_props[target_id_str] = {
                'target_id': target_id_str,
                'target_name': record.get(SCHEMA.TARGET_NAME),
                'type': record.get(SCHEMA.TYPE),
                'color': target_color_hex(target_id_str),
            }

        features = []
        for target_id, coordinates in target_points.items():
            if len(coordinates) < 2:
                continue

            if not fade_segments:
                features.append(
                    {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'LineString',
                            'coordinates': coordinates,
                        },
                        'properties': {
                            **target_props[target_id],
                        },
                    }
                )
                continue

            total_segments = len(coordinates) - 1
            min_alpha = 0.0
            max_alpha = 1.0
            alpha_range = max_alpha - min_alpha

            for segment_index in range(total_segments):
                start_coord = coordinates[segment_index]
                end_coord = coordinates[segment_index + 1]
                progress = (segment_index + 1) / total_segments
                eased_progress = progress**2.8
                alpha = min_alpha + (alpha_range * eased_progress)

                features.append(
                    {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'LineString',
                            'coordinates': [start_coord, end_coord],
                        },
                        'properties': {
                            **target_props[target_id],
                            'alpha': alpha,
                        },
                    }
                )

        geojson = {'type': 'FeatureCollection', 'features': features}
        self.send_cmd(command='update_trails', data=geojson)
