# backend/auth/user_auth.py

import mysql.connector

class UserAuthManager:
    def __init__(self, db_config: dict):
        """
        db_config 예시:
        {
            "host": "localhost",
            "user": "root",
            "password": "yourpassword",
            "database": "dust"
        }
        """
        try:
            self.conn = mysql.connector.connect(**db_config)
            self.cursor = self.conn.cursor()
            print("[✅ DB 연결 성공]")
        except mysql.connector.Error as err:
            print(f"[❌ DB 연결 실패] {err}")
            raise

    def verify_user(self, username: str, password: str):
        """
        입력된 username과 password를 users 테이블에서 검사하여
        인증에 성공하면 (True, role)을 반환하고,
        실패하면 (False, None)을 반환합니다.
        """
        query = "SELECT password, role FROM users WHERE username = %s"
        self.cursor.execute(query, (username,))
        row = self.cursor.fetchone()

        if row:
            stored_password, role = row
            if stored_password == password:
                print(f"[✅ 로그인 성공] {username} ({role})")
                return True, role
            else:
                print(f"[⚠️ 비밀번호 불일치] {username}")
        else:
            print(f"[❌ 사용자 없음] {username}")

        return False, None

    def close(self):
        self.cursor.close()
        self.conn.close()
