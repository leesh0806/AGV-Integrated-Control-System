import mysql.connector
from datetime import datetime
from typing import List, Dict, Any

class BatteryDB:
    def __init__(self, host, user, password, database):
        self.conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        self.cursor = self.conn.cursor(dictionary=True)  # 딕셔너리 형태로 결과 반환
        self._create_table()

    def _create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS battery_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            truck_id VARCHAR(50) NOT NULL,
            battery_level FLOAT NOT NULL,
            truck_state VARCHAR(50) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_truck_id (truck_id),
            INDEX idx_timestamp (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"[DB 오류] {err}")
            self.conn.rollback()

    def log_battery_status(self, truck_id: str, battery_level: float, truck_state: str, event_type: str):
        query = """
        INSERT INTO battery_logs (truck_id, battery_level, truck_state, event_type)
        VALUES (%s, %s, %s, %s)
        """
        try:
            self.cursor.execute(query, (truck_id, battery_level, truck_state, event_type))
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"[DB 오류] {err}")
            self.conn.rollback()

    def get_battery_history(self, truck_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        배터리 히스토리 조회
        :return: [{"id": 1, "truck_id": "TRUCK_01", "battery_level": 85.5, ...}, ...]
        """
        query = """
        SELECT 
            id,
            truck_id,
            battery_level,
            truck_state,
            event_type,
            timestamp
        FROM battery_logs 
        WHERE truck_id = %s 
        ORDER BY timestamp DESC 
        LIMIT %s
        """
        try:
            self.cursor.execute(query, (truck_id, limit))
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"[DB 오류] {err}")
            return []

    def close(self):
        """DB 연결 종료"""
        try:
            self.cursor.close()
            self.conn.close()
        except mysql.connector.Error as err:
            print(f"[DB 오류] 연결 종료 중 오류 발생: {err}") 