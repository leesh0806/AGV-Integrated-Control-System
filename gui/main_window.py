# frontend/gui/main_window.py

from PyQt6.QtWidgets import QMainWindow
from PyQt6 import uic
import os

class MainWindow(QMainWindow):
    def __init__(self, role):
        super().__init__()
        self.role = role  # 아직 사용 안함

        ui_path = os.path.join(os.path.dirname(__file__), "ui", "main.ui")
        uic.loadUi(ui_path, self)

        self.setWindowTitle("운송관제 시스템 - 메인 화면")
