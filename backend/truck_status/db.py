import mysql.connector
from datetime import datetime
from typing import List, Dict, Optional

class TruckStatusDB:
    def __init__(self, host: str, user: str, password: str, database: str):
        self.conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        self.cursor = self.conn.cursor(dictionary=True)
        self._create_tables()

    def _create_tables(self):
        # 배터리 로그 테이블
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS battery_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                truck_id VARCHAR(20) NOT NULL,
                battery_level FLOAT NOT NULL,
                truck_state VARCHAR(20) NOT NULL,
                event_type VARCHAR(20) NOT NULL,
                timestamp DATETIME NOT NULL,
                INDEX idx_truck_timestamp (truck_id, timestamp)
            )
        """)
        
        # 위치 로그 테이블
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS position_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                truck_id VARCHAR(20) NOT NULL,
                position VARCHAR(20) NOT NULL,
                state VARCHAR(20) NOT NULL,
                timestamp DATETIME NOT NULL,
                INDEX idx_truck_timestamp (truck_id, timestamp)
            )
        """)
        self.conn.commit()

    def log_battery_status(self, truck_id: str, battery_level: float, truck_state: str, event_type: str):
        """배터리 상태 로깅"""
        query = """
            INSERT INTO battery_logs (truck_id, battery_level, truck_state, event_type, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (truck_id, battery_level, truck_state, event_type, datetime.now()))
        self.conn.commit()

    def log_position_status(self, truck_id: str, position: str, state: str):
        """위치 상태 로깅"""
        query = """
            INSERT INTO position_logs (truck_id, position, state, timestamp)
            VALUES (%s, %s, %s, %s)
        """
        self.cursor.execute(query, (truck_id, position, state, datetime.now()))
        self.conn.commit()

    def get_latest_battery_status(self, truck_id: str) -> Optional[Dict]:
        """최신 배터리 상태 조회"""
        query = """
            SELECT battery_level, truck_state, event_type, timestamp
            FROM battery_logs
            WHERE truck_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """
        self.cursor.execute(query, (truck_id,))
        return self.cursor.fetchone()

    def get_latest_position_status(self, truck_id: str) -> Optional[Dict]:
        """최신 위치 상태 조회"""
        query = """
            SELECT position, state, timestamp
            FROM position_logs
            WHERE truck_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """
        self.cursor.execute(query, (truck_id,))
        return self.cursor.fetchone()

    def get_battery_history(self, truck_id: str, limit: int = 100) -> List[Dict]:
        """배터리 히스토리 조회"""
        query = """
            SELECT battery_level, truck_state, event_type, timestamp
            FROM battery_logs
            WHERE truck_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        self.cursor.execute(query, (truck_id, limit))
        return self.cursor.fetchall()

    def get_position_history(self, truck_id: str, limit: int = 100) -> List[Dict]:
        """위치 히스토리 조회"""
        query = """
            SELECT position, state, timestamp
            FROM position_logs
            WHERE truck_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        self.cursor.execute(query, (truck_id, limit))
        return self.cursor.fetchall()

    def close(self):
        """리소스 정리"""
        self.cursor.close()
        self.conn.close() 