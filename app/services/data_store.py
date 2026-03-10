from datetime import UTC, datetime, timedelta
from typing import Any

import polars as pl
from PySide6.QtCore import QObject, QTimer, Signal

from app.constants.data_schema import SCHEMA


class DataStore(QObject):
    data_added = Signal(dict)
    data_updated = Signal()

    def __init__(self, max_rows: int = 100000, auto_cleanup_hours: int = 24) -> None:
        super().__init__()
        self._max_rows = max_rows
        self._auto_cleanup_hours = auto_cleanup_hours
        self._batch_timeout_ms = 1000

        self._df = pl.DataFrame(
            schema={
                SCHEMA.DATETIME: pl.Datetime('ms', 'UTC'),
                SCHEMA.TYPE: pl.String,
                SCHEMA.TARGET_ID: pl.String,
                SCHEMA.TARGET_NAME: pl.String,
                SCHEMA.LATITUDE: pl.Float64,
                SCHEMA.LONGITUDE: pl.Float64,
                SCHEMA.HEIGHT: pl.Float64,
                SCHEMA.SPEED: pl.Float64,
            }
        )
        self._batch: list[dict[str, Any]] = []

        self._batch_timer = QTimer(self)
        self._batch_timer.timeout.connect(self._flush_batch)
        self._batch_timer.setSingleShot(True)

    def add_data(self, data: dict[str, Any]) -> None:
        """Add single data point (batched)"""
        data[SCHEMA.DATETIME] = datetime.fromisoformat(data[SCHEMA.DATETIME])

        self._batch.append(data)
        
        if not self._batch_timer.isActive():
            self._batch_timer.start(self._batch_timeout_ms)

    def _flush_batch(self) -> None:
        """Flush batched data to DataFrame"""
        if not self._batch:
            return

        new_df = pl.DataFrame(self._batch, schema=self._df.schema)
        self._df = pl.concat([self._df, new_df], how='vertical_relaxed')
        self._batch.clear()

        # Cleanup by size
        if len(self._df) > self._max_rows:
            self._df = self._df.tail(self._max_rows)

        # Clean by time
        cutoff = datetime.now(UTC) - timedelta(hours=self._auto_cleanup_hours)
        self._df = self._df.filter(pl.col(SCHEMA.DATETIME) > cutoff)

        self.data_updated.emit()

    def filter_by_time(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Filter by time range"""
        self._flush_batch()
        return self._df.filter(
            (pl.col(SCHEMA.DATETIME) >= start) & (pl.col(SCHEMA.DATETIME) <= end)
        )

    def filter_by_target(self, target_id: str) -> pl.DataFrame:
        """Get all data for specific target"""
        self._flush_batch()
        return self._df.filter(pl.col(SCHEMA.TARGET_ID) == target_id)

    def get_latest_for_target(self, target_id: str) -> dict[str, Any] | None:
        """Get the most recent row for a specific target."""
        target_df = self.filter_by_target(target_id)
        if target_df.is_empty():
            return None
        latest_row = target_df.sort(SCHEMA.DATETIME, descending=False).row(-1, named=True)
        return latest_row

    def get_latest_per_target(self) -> pl.DataFrame:
        """Get most recent data for each target"""
        self._flush_batch()
        return self._df.group_by(SCHEMA.TARGET_ID).agg(pl.all().sort_by(SCHEMA.DATETIME).last())

    def get_trail_points_per_target(self, max_points_per_target: int = 200) -> pl.DataFrame:
        """Get recent ordered trail points per target.

        Returns a DataFrame with one row per point, sorted by target and datetime,
        containing only valid coordinates.
        """
        self._flush_batch()

        if self._df.is_empty():
            return self._df.clear()

        trail_df = (
            self._df
            .filter(
                pl.col(SCHEMA.LATITUDE).is_not_null()
                & pl.col(SCHEMA.LONGITUDE).is_not_null()
            )
            .sort([SCHEMA.TARGET_ID, SCHEMA.DATETIME])
        )

        if max_points_per_target > 0:
            trail_df = trail_df.group_by(
                SCHEMA.TARGET_ID,
                maintain_order=True,
            ).tail(max_points_per_target)

        return trail_df

    def sort_by_time(self, descending: bool = False) -> pl.DataFrame:
        """Sort by time"""
        self._flush_batch()
        return self._df.sort(SCHEMA.DATETIME, descending=descending)

    def filter_custom(self, expression: pl.Expr) -> pl.DataFrame:
        """Filter with custom Polars expression"""
        self._flush_batch()
        return self._df.filter(expression)

    def get_all_data(self) -> pl.DataFrame:
        """Get all data"""
        self._flush_batch()
        return self._df.clone()

    def clear(self) -> None:
        """Clear all data"""
        self._batch_timer.stop()
        self._batch.clear()
        self._df = self._df.clear()
        self.data_updated.emit()
    
    def delete_target(self, target_id: str) -> None:
        """Delete all detections for a given target ID"""
        self._flush_batch()
        self._df = self._df.filter(pl.col(SCHEMA.TARGET_ID) != target_id)
        self.data_updated.emit()

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about stored data"""
        self._flush_batch()
        return {
            'total_rows': len(self._df),
            'unique_targets': self._df[SCHEMA.TARGET_ID].n_unique(),
            'time_range': {
                'start': self._df[SCHEMA.DATETIME].min(),
                'end': self._df[SCHEMA.DATETIME].max(),
            },
            'memory_mb': self._df.estimated_size('mb'),
        }
