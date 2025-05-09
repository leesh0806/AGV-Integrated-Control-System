from datetime import datetime
from typing import Optional, List, Dict
import sqlite3

class TruckStatusDB:
    def __init__(self, db_path: str = "truck_status.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 배터리 상태 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS battery_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    truck_id TEXT NOT NULL,
                    battery_level REAL NOT NULL,
                    truck_status TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 위치 상태 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    truck_id TEXT NOT NULL,
                    location TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()

    def log_battery_status(self, truck_id: str, battery_level: float, truck_status: str, event_type: str):
        """배터리 상태 로깅"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO battery_status (truck_id, battery_level, truck_status, event_type)
                VALUES (?, ?, ?, ?)
            """, (truck_id, battery_level, truck_status, event_type))
            conn.commit()

    def log_position_status(self, truck_id: str, location: str, status: str):
        """위치 상태 로깅"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO position_status (truck_id, location, status)
                VALUES (?, ?, ?)
            """, (truck_id, location, status))
            conn.commit()

    def get_latest_battery_status(self, truck_id: str) -> Optional[Dict]:
        """최신 배터리 상태 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT battery_level, truck_status, event_type, timestamp
                FROM battery_status
                WHERE truck_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (truck_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "battery_level": row[0],
                    "truck_status": row[1],
                    "event_type": row[2],
                    "timestamp": row[3]
                }
            return None

    def get_latest_position_status(self, truck_id: str) -> Optional[Dict]:
        """최신 위치 상태 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT location, status, timestamp
                FROM position_status
                WHERE truck_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (truck_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "location": row[0],
                    "status": row[1],
                    "timestamp": row[2]
                }
            return None

    def get_battery_history(self, truck_id: str, limit: int = 100) -> List[Dict]:
        """배터리 상태 히스토리 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT battery_level, truck_status, event_type, timestamp
                FROM battery_status
                WHERE truck_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (truck_id, limit))
            
            return [{
                "battery_level": row[0],
                "truck_status": row[1],
                "event_type": row[2],
                "timestamp": row[3]
            } for row in cursor.fetchall()]

    def get_position_history(self, truck_id: str, limit: int = 100) -> List[Dict]:
        """위치 상태 히스토리 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT location, status, timestamp
                FROM position_status
                WHERE truck_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (truck_id, limit))
            
            return [{
                "location": row[0],
                "status": row[1],
                "timestamp": row[2]
            } for row in cursor.fetchall()] 