from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class _PopupCloseFilter(QObject):
    """Event filter that intercepts close on a popup window and pops it back in."""

    def __init__(self, tab: 'DetachableTab') -> None:
        super().__init__(tab)
        self._tab = tab

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Close:
            self._tab._pop_in()
            return True
        return super().eventFilter(obj, event)


class DetachableTab(QWidget):
    """Generic tab widget whose content can be detached into a floating window.

    The *content* widget must implement:
    - ``pop_requested = Signal()`` — emitted when the user clicks the pop button.
    - ``set_popped_out(popped: bool) -> None`` — called after each transition so
      the content can update its own button label / checked state.

    No knowledge of the pop button itself leaks into this class.
    """

    def __init__(
        self,
        content: QWidget,
        window_title: str,
        placeholder_text: str = 'Content is shown in a separate window.',
    ) -> None:
        super().__init__()
        self._content = content
        self._window_title = window_title
        self._popup: QWidget | None = None
        self._close_filter: _PopupCloseFilter | None = None

        content.pop_requested.connect(self._toggle_pop)  # type: ignore[attr-defined]

        self._embed_container = QWidget()
        embed_layout = QVBoxLayout(self._embed_container)
        embed_layout.setContentsMargins(0, 0, 0, 0)
        embed_layout.addWidget(content)

        self._placeholder = QLabel(placeholder_text)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._embed_container)
        layout.addWidget(self._placeholder)

    def _toggle_pop(self) -> None:
        if self._popup is None:
            self._pop_out()
        else:
            self._pop_in()

    def _pop_out(self) -> None:
        popup = QWidget(None, Qt.WindowType.Window)
        popup.setWindowTitle(self._window_title)
        popup.resize(640, 480)

        popup_layout = QVBoxLayout(popup)
        popup_layout.setContentsMargins(4, 4, 4, 4)

        self._content.setParent(popup)
        popup_layout.addWidget(self._content)

        self._close_filter = _PopupCloseFilter(self)
        popup.installEventFilter(self._close_filter)

        self._popup = popup
        self._embed_container.hide()
        self._placeholder.show()
        self._content.set_popped_out(True)  # type: ignore[attr-defined]
        popup.show()

    def _pop_in(self) -> None:
        if self._popup is None:
            return

        popup = self._popup
        if self._close_filter is not None:
            popup.removeEventFilter(self._close_filter)
            self._close_filter = None

        self._content.setParent(self._embed_container)
        embed_layout = self._embed_container.layout()
        if embed_layout is not None:
            embed_layout.addWidget(self._content)
        self._content.show()

        self._popup = None
        popup.close()

        self._embed_container.show()
        self._placeholder.hide()
        self._content.set_popped_out(False)  # type: ignore[attr-defined]
