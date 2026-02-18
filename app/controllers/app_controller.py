from app.models.app_model import AppModel
from app.views.main_window import MainWindow


class AppController:
    def __init__(self, model: AppModel, view: MainWindow):
        self._model = model
        self._view = view
