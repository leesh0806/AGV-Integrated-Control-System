# run_gui.py

from PyQt6.QtWidgets import QApplication
from gui.login_window import LoginWindow
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec())
