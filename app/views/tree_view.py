import math
from typing import Any

import polars as pl
from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QResizeEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.constants.data_schema import SCHEMA
from app.utils.target_color import target_color_hex, target_text_color_hex


class TargetTreeWidget(QTreeWidget):
    delete_target_by_id = Signal(str)
    view_target_on_map = Signal(str)

    COLUMN_LABELS = {
        SCHEMA.TARGET_NAME: 'Name',
        SCHEMA.TARGET_ID: 'ID',
        SCHEMA.DATETIME: 'Date/Time',
    }

    def __init__(self) -> None:
        super().__init__()
        self.setColumnCount(3)
        self.setHeaderLabels(list(self.COLUMN_LABELS.values()))
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(True)
        self.setIndentation(7)

        header = self.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.resizeSection(0, 150)
        header.resizeSection(1, 100)
        header.resizeSection(2, 150)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._item_by_id: dict[str, QTreeWidgetItem] = {}

    def _get_column_index(self, schema_key: str) -> int | None:
        """Get column index by schema key, returns None if not found"""
        target_label = self.COLUMN_LABELS.get(schema_key)
        if target_label is None:
            return None

        for col in range(self.columnCount()):
            header_item = self.headerItem()
            if header_item and header_item.text(col) == target_label:
                return col
        return None

    def update_tree(self, df: pl.DataFrame) -> None:
        """Update tree with new data"""
        if df.is_empty():
            self.clear()
            self._item_by_id.clear()
            return
        df = df.sort(SCHEMA.DATETIME, descending=False)
        target_id_col = self._get_column_index(SCHEMA.TARGET_ID)

        # Store current selection before modifying tree
        selected_target_id, selected_child_index = self._store_selection()

        # Update or create parent items in exact row order
        ordered_target_ids: list[str] = []
        for row_index, row in enumerate(df.iter_rows(named=True)):
            target_id = row[SCHEMA.TARGET_ID]
            ordered_target_ids.append(target_id)
            target_name = row[SCHEMA.TARGET_NAME] or ''
            datetime_val = row[SCHEMA.DATETIME] or ''

            # Reuse parent item if exists, create new if not
            parent_item = self._item_by_id.get(target_id)
            if parent_item is None:
                parent_item = QTreeWidgetItem()
                self.insertTopLevelItem(row_index, parent_item)
                self._item_by_id[target_id] = parent_item
            else:
                current_index = self.indexOfTopLevelItem(parent_item)
                if current_index != row_index and current_index >= 0:
                    moved_item = self.takeTopLevelItem(current_index)
                    if moved_item is not None:
                        self.insertTopLevelItem(row_index, moved_item)

            # Update parent item data
            parent_item.setText(0, target_name)
            parent_item.setText(1, target_id)
            parent_item.setText(2, str(datetime_val))
            if target_id_col is not None:
                bg_color = target_color_hex(target_id)
                fg_color = target_text_color_hex(bg_color)
                parent_item.setBackground(target_id_col, QColor(bg_color))
                parent_item.setForeground(target_id_col, QColor(fg_color))

            # Save expanded state before rebuilding children
            expanded = parent_item.isExpanded()
            parent_item.takeChildren()
            self._rebuild_children(parent_item, row)
            parent_item.setExpanded(expanded)

        # Remove stale items (targets no longer in data)
        current_target_ids = set(ordered_target_ids)
        stale_ids = set(self._item_by_id.keys()) - current_target_ids
        for target_id in stale_ids:
            item = self._item_by_id.pop(target_id)
            index = self.indexOfTopLevelItem(item)
            if index >= 0:
                self.takeTopLevelItem(index)

        # Restore selection
        self._restore_selection(selected_target_id, selected_child_index)

    def _store_selection(self) -> tuple[str | None, int | None]:
        """Store current selection info before tree updates"""
        current_item = self.currentItem()
        selected_target_id: str | None = None
        selected_child_index: int | None = None

        if current_item:
            if current_item.parent() is not None:
                # Child item selected
                parent = current_item.parent()
                selected_child_index = parent.indexOfChild(current_item)
                for target_id, item in self._item_by_id.items():
                    if item is parent:
                        selected_target_id = target_id
                        break
            else:
                # Parent item selected
                for target_id, item in self._item_by_id.items():
                    if item is current_item:
                        selected_target_id = target_id
                        break

        return selected_target_id, selected_child_index

    def _rebuild_children(
        self, parent_item: QTreeWidgetItem, row: dict[str, Any]
    ) -> None:
        """Rebuild child items for a parent from row data"""
        fields = [
            (SCHEMA.TYPE, 'Type'),
            (SCHEMA.LATITUDE, 'Latitude'),
            (SCHEMA.LONGITUDE, 'Longitude'),
            (SCHEMA.HEIGHT, 'Height'),
            (SCHEMA.SPEED, 'Speed'),
        ]

        for field_key, field_label in fields:
            if field_key in row:
                value = row[field_key]
                if value is None:
                    value = ''
                elif field_key in [SCHEMA.LATITUDE, SCHEMA.LONGITUDE]:
                    value = f'{value:.6f}'

                child_item = QTreeWidgetItem(parent_item)
                child_item.setText(0, field_label)
                child_item.setText(1, str(value))

    def _restore_selection(
        self, selected_target_id: str | None, selected_child_index: int | None
    ) -> None:
        """Restore selection after tree updates"""
        if selected_target_id and selected_target_id in self._item_by_id:
            parent_item = self._item_by_id[selected_target_id]
            if (
                selected_child_index is not None
                and selected_child_index < parent_item.childCount()
            ):
                # Restore child selection
                child_item = parent_item.child(selected_child_index)
                self.setCurrentItem(child_item)
            else:
                # Restore parent selection
                self.setCurrentItem(parent_item)

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu - only for parent items"""
        item = self.itemAt(position)
        if not item:
            return

        # Only show menu for parent items (targets)
        if item.parent() is not None:
            return

        # Extract target_id immediately to avoid stale item reference
        col_index = self._get_column_index(SCHEMA.TARGET_ID)
        if col_index is None:
            return
        target_id = item.text(col_index)

        menu = QMenu(self)

        view_map_action = QAction('View on Map', self)
        view_map_action.triggered.connect(
            lambda: self.view_target_on_map.emit(target_id)
        )
        menu.addAction(view_map_action)

        delete_action = QAction('Delete Target', self)
        delete_action.triggered.connect(
            lambda: self.delete_target_by_id.emit(target_id)
        )
        menu.addAction(delete_action)

        menu.exec(self.viewport().mapToGlobal(position))


class TreeView(QWidget):
    delete_target_by_id = Signal(str)
    view_target_on_map = Signal(str)
    RESIZE_DEBOUNCE_MS = 120

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._tree = TargetTreeWidget()
        self._tree.view_target_on_map.connect(self.view_target_on_map.emit)
        self._tree.delete_target_by_id.connect(self.delete_target_by_id.emit)

        pager_layout = QHBoxLayout()
        pager_layout.setContentsMargins(4, 0, 4, 0)
        pager_layout.setSpacing(8)

        self._prev_button = QPushButton('Previous')
        self._next_button = QPushButton('Next')
        self._page_label = QLabel('Page 1 / 1')
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._prev_button.clicked.connect(self._go_to_previous_page)
        self._next_button.clicked.connect(self._go_to_next_page)

        pager_layout.addWidget(self._prev_button)
        pager_layout.addWidget(self._page_label, 1)
        pager_layout.addWidget(self._next_button)

        layout.addWidget(self._tree)
        layout.addLayout(pager_layout)

        self._latest_df = pl.DataFrame()
        self._current_page = 1
        self._total_pages = 1
        self._page_size = 1
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._apply_resized_page_size)
        self._update_pagination_ui()

    def update_tree(self, df: pl.DataFrame) -> None:
        """Update paged tree data and keep current page when possible."""
        self._latest_df = df.sort(SCHEMA.DATETIME, descending=False)
        self._page_size = max(1, self._calculate_page_size())

        row_count = self._latest_df.height
        self._total_pages = max(1, math.ceil(row_count / self._page_size))
        if self._current_page > self._total_pages:
            self._current_page = self._total_pages

        self._render_current_page()

    def _render_current_page(self) -> None:
        if self._latest_df.is_empty():
            self._tree.update_tree(self._latest_df)
            self._update_pagination_ui()
            return

        start_idx = (self._current_page - 1) * self._page_size
        page_df = self._latest_df.slice(start_idx, self._page_size)
        self._tree.update_tree(page_df)
        self._update_pagination_ui()

    def _calculate_page_size(self) -> int:
        """Estimate how many top-level rows fit in the current tree viewport."""
        viewport_height = max(0, self._tree.viewport().height())
        row_height = self._tree.sizeHintForRow(0)
        if row_height <= 0:
            # Hard minimum; extra padding on top of font
            row_height = max(18, self._tree.fontMetrics().height() + 6)

        return max(1, viewport_height // row_height)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._resize_timer.start(self.RESIZE_DEBOUNCE_MS)

    def _apply_resized_page_size(self) -> None:
        new_page_size = max(1, self._calculate_page_size())
        if new_page_size == self._page_size:
            return

        first_visible_index = (self._current_page - 1) * self._page_size
        self._page_size = new_page_size

        row_count = self._latest_df.height
        self._total_pages = max(1, math.ceil(row_count / max(1, self._page_size)))
        self._current_page = max(1, (first_visible_index // self._page_size) + 1)
        if self._current_page > self._total_pages:
            self._current_page = self._total_pages

        self._render_current_page()

    def _go_to_previous_page(self) -> None:
        if self._current_page <= 1:
            return

        self._current_page -= 1
        self._render_current_page()

    def _go_to_next_page(self) -> None:
        if self._current_page >= self._total_pages:
            return

        self._current_page += 1
        self._render_current_page()

    def _update_pagination_ui(self) -> None:
        self._page_label.setText(f'Page {self._current_page} / {self._total_pages}')
        self._prev_button.setEnabled(self._current_page > 1)
        self._next_button.setEnabled(self._current_page < self._total_pages)
