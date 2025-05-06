import sys
from PyQt6.QtWidgets import QApplication
from gui.login_window import LoginWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    exit_code = app.exec()
    sys.exit(exit_code) 