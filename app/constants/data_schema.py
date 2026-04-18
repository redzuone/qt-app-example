from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class DataSchema:
    DATETIME: Final[str] = 'datetime'
    FIRST_SEEN: Final[str] = 'first_seen'
    TYPE: Final[str] = 'type'
    TARGET_ID: Final[str] = 'target_id'
    TARGET_NAME: Final[str] = 'target_name'
    LATITUDE: Final[str] = 'latitude'
    LONGITUDE: Final[str] = 'longitude'
    HEIGHT: Final[str] = 'height'
    SPEED: Final[str] = 'speed'
    STATION_ID: Final[str] = 'station_id'
    FREQUENCY: Final[str] = 'freq'
    BEARING: Final[str] = 'bearing'


SCHEMA = DataSchema()
