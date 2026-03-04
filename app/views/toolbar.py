from PySide6.QtGui import QAction
from PySide6.QtWidgets import QStyle, QToolBar


class ToolBar(QToolBar):
    """Main toolbar."""

    def __init__(self) -> None:
        super().__init__()
        self.setMovable(False)

        self._add_dummy_actions()

    def _add_dummy_actions(self) -> None:
        style = self.style()

        new_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_FileIcon),
            'New',
            self,
        )
        new_action.setStatusTip('Create a new item')
        self.addAction(new_action)

        open_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton),
            'Open',
            self,
        )
        open_action.setStatusTip('Open an existing item')
        self.addAction(open_action)

        save_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            'Save',
            self,
        )
        save_action.setStatusTip('Save current changes')
        self.addAction(save_action)

        self.addSeparator()

        refresh_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
            'Refresh',
            self,
        )
        refresh_action.setStatusTip('Refresh content')
        self.addAction(refresh_action)

        search_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            'Search',
            self,
        )
        search_action.setStatusTip('Search items')
        self.addAction(search_action)

        settings_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
            'Settings',
            self,
        )
        settings_action.setStatusTip('Open settings')
        self.addAction(settings_action)

        self.addSeparator()

        help_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton),
            'Help',
            self,
        )
        help_action.setStatusTip('Open help')
        self.addAction(help_action)
