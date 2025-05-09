import mysql.connector
from datetime import datetime
from typing import Optional, List, Dict

class TruckStatusDB:
    def __init__(self, host="localhost", user="root", password="jinhyuk2dacibul", database="dust"):
        self.connection_params = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.init_db()

    def get_connection(self):
        return mysql.connector.connect(**self.connection_params)

    def init_db(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 배터리 상태 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS battery_status (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    truck_id VARCHAR(50),
                    battery_level FLOAT,
                    truck_status VARCHAR(50),
                    event_type VARCHAR(50),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
            """)

            # 위치 상태 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_status (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    truck_id VARCHAR(50),
                    location VARCHAR(50),
                    status VARCHAR(50),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            print("[DEBUG] 트럭 상태 데이터베이스 초기화 완료")
        
        except mysql.connector.Error as err:
            print(f"[ERROR] DB 초기화 실패: {err}")

    def log_battery_status(self, truck_id: str, battery_level: float, truck_status: str, event_type: str):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO battery_status (truck_id, battery_level, truck_status, event_type)
                VALUES (%s, %s, %s, %s)
            """, (truck_id, battery_level, truck_status, event_type))
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"[ERROR] 배터리 상태 로깅 실패: {err}")

    def log_position_status(self, truck_id: str, location: str, status: str):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO position_status (truck_id, location, status)
                VALUES (%s, %s, %s)
            """, (truck_id, location, status))
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"[ERROR] 위치 상태 로깅 실패: {err}")

    def get_latest_battery_status(self, truck_id: str) -> Optional[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT battery_level, truck_status, event_type, timestamp
                FROM battery_status
                WHERE truck_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (truck_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row if row else None
        except mysql.connector.Error as err:
            print(f"[ERROR] 배터리 상태 조회 실패: {err}")
            return None

    def get_latest_position_status(self, truck_id: str) -> Optional[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT location, status, timestamp
                FROM position_status
                WHERE truck_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (truck_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row if row else None
        except mysql.connector.Error as err:
            print(f"[ERROR] 위치 상태 조회 실패: {err}")
            return None

    def get_battery_history(self, truck_id: str, limit: int = 100) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT battery_level, truck_status, event_type, timestamp
                FROM battery_status
                WHERE truck_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (truck_id, limit))
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
        except mysql.connector.Error as err:
            print(f"[ERROR] 배터리 히스토리 조회 실패: {err}")
            return []

    def get_position_history(self, truck_id: str, limit: int = 100) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT location, status, timestamp
                FROM position_status
                WHERE truck_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (truck_id, limit))
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
        except mysql.connector.Error as err:
            print(f"[ERROR] 위치 히스토리 조회 실패: {err}")
            return []

    def close(self):
        print("[DEBUG] TruckStatusDB 리소스 정리 완료")
