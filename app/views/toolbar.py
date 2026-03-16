from PySide6.QtWidgets import QToolBar


class ToolBar(QToolBar):
    """Main toolbar."""

    def __init__(self) -> None:
        super().__init__()
        self.setMovable(False)
