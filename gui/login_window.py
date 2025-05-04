# frontend/gui/login_window.py

from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6 import uic
import os
from backend.auth.user_auth import UserAuthManager
from gui.main_window import MainWindow  # 나중에 연결

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # UI 파일 경로 (절대경로 또는 상대경로 가능)
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "login.ui")
        uic.loadUi(ui_path, self)

        # 버튼 및 입력창 objectName이 login.ui에 있어야 합니다
        # 예: QLineEdit (input_id, input_pw), QPushButton (btn_login)

        # DB 인증 관리자 설정
        self.auth_manager = UserAuthManager({
            "host": "localhost",
            "user": "root",
            "password": "jinhyuk2dacibul",
            "database": "dust"
        })

        # 로그인 버튼 이벤트 연결
        self.btn_login.clicked.connect(self.handle_login)

    def handle_login(self):
        username = self.input_id.text().strip()
        password = self.input_pw.text().strip()

        success, role = self.auth_manager.verify_user(username, password)
        if success:
            self.open_main(role)
        else:
            QMessageBox.warning(self, "로그인 실패", "❌ 아이디 또는 비밀번호가 잘못되었습니다.")

    def open_main(self, role):
        # 로그인 성공 → 메인 창 열기 (나중에 구현)
        self.main = MainWindow(role)
        self.main.show()
        self.close()
