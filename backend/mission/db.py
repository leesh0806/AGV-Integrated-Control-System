# backend/mission/db.py

import pymysql
from typing import List, Optional, Tuple, Any, Dict
from datetime import datetime

class MissionDB: 
    def __init__(self, host: str, user: str, password: str, database: str):
        self.connection_params = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.Cursor
        }
        self._init_db()
    
    # DB 초기화
    def _init_db(self) -> None:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id VARCHAR(36) PRIMARY KEY,
                    cargo_type VARCHAR(100) NOT NULL,
                    cargo_amount FLOAT NOT NULL,
                    source VARCHAR(100) NOT NULL,
                    destination VARCHAR(100) NOT NULL,
                    status_code VARCHAR(50) NOT NULL,
                    status_label VARCHAR(100) NOT NULL,
                    assigned_truck_id VARCHAR(20),
                    timestamp_created DATETIME NOT NULL,
                    timestamp_assigned DATETIME,
                    timestamp_completed DATETIME,
                    INDEX idx_status (status_code),
                    INDEX idx_truck (assigned_truck_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            print("[DB] 미션 테이블 준비 완료")
        except Exception as e:
            print(f"[DB ERROR] 초기화 중 오류 발생: {e}")
    
    # DB 연결 반환
    def get_connection(self) -> pymysql.connections.Connection:
        return pymysql.connect(**self.connection_params)
    
    # ------------------ 쿼리 실행 ----------------------------

    # 쿼리 실행 및 결과 반환
    def execute(self, query: str, params: Tuple = None) -> List[Tuple]:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if query.strip().upper().startswith(('SELECT', 'SHOW')):
                result = cursor.fetchall()
            else:
                conn.commit()
                result = None
            return result
        except Exception as e:
            conn.rollback()
            print(f"[DB ERROR] 쿼리 실행 중 오류 발생: {e}")
            print(f"쿼리: {query}")
            print(f"파라미터: {params}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    # 트랜잭션 실행
    def execute_transaction(self, queries: List[Dict[str, Any]]) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            for query_data in queries:
                cursor.execute(query_data['query'], query_data.get('params', None))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"[DB ERROR] 트랜잭션 실행 중 오류 발생: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    # ------------------ 미션 저장 ----------------------------

    # 미션 저장
    def save_mission(self, mission_data: Tuple) -> bool:
        try:
            query = """
                INSERT INTO missions (
                    mission_id, cargo_type, cargo_amount, source, destination,
                    status_code, status_label, assigned_truck_id,
                    timestamp_created, timestamp_assigned, timestamp_completed
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    status_code = VALUES(status_code),
                    status_label = VALUES(status_label),
                    assigned_truck_id = VALUES(assigned_truck_id),
                    timestamp_assigned = VALUES(timestamp_assigned),
                    timestamp_completed = VALUES(timestamp_completed)
            """
            self.execute(query, mission_data)
            return True
        except Exception as e:
            print(f"[DB ERROR] 미션 저장 중 오류 발생: {e}")
            return False
    
    # ------------------ 미션 조회 ----------------------------

    # 대기 미션 조회
    def get_waiting_missions(self) -> List[Tuple]:
        try:
            query = """
                SELECT * FROM missions 
                WHERE status_code = 'WAITING'
                ORDER BY timestamp_created ASC
            """
            return self.execute(query)
        except Exception as e:
            print(f"[DB ERROR] 대기 미션 조회 중 오류 발생: {e}")
            return []
    
        # 대기 중인 미션 ID 조회
    
    # 대기 중인 미션 ID 조회
    def get_waiting_mission_ids(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT mission_id 
            FROM missions
            WHERE status_code = 'WAITING'
            AND assigned_truck_id IS NULL
            ORDER BY timestamp_created ASC
            """
            cursor.execute(query)
            db_missions = cursor.fetchall()
            
            # 미션 ID 집합 구성
            db_mission_ids = {mission[0] for mission in db_missions}
            
            cursor.close()
            conn.close()
            
            return db_mission_ids
            
        except Exception as e:
            print(f"[ERROR] 대기 중인 미션 ID 조회 중 오류 발생: {e}")
            return set()

    # 할당된 미션과 대기 미션 조회
    def get_assigned_and_waiting_missions(self) -> List[Tuple]:
        try:
            query = """
                SELECT * FROM missions 
                WHERE status_code IN ('WAITING', 'ASSIGNED') 
                ORDER BY timestamp_created ASC
            """
            return self.execute(query)
        except Exception as e:
            print(f"[DB ERROR] 미션 조회 중 오류 발생: {e}")
            return []
    
    # 미션 ID로 미션 조회
    def find_mission_by_id(self, mission_id: str) -> Optional[Tuple]:
        """미션 ID로 미션 조회"""
        try:
            query = "SELECT * FROM missions WHERE mission_id = %s"
            result = self.execute(query, (mission_id,))
            return result[0] if result else None
        except Exception as e:
            print(f"[DB ERROR] 미션 조회 중 오류 발생: {e}")
            return None
    
    # 트럭 ID로 미션 조회
    def get_missions_by_truck(self, truck_id: str) -> List[Tuple]:
        """트럭 ID로 할당된 미션 목록 조회"""
        try:
            query = """
                SELECT * FROM missions 
                WHERE assigned_truck_id = %s 
                AND status_code = 'ASSIGNED'
                ORDER BY timestamp_assigned ASC
            """
            return self.execute(query, (truck_id,))
        except Exception as e:
            print(f"[DB ERROR] 트럭 미션 조회 중 오류 발생: {e}")
            return []
    
    # 현재 시스템의 미션 통계 반환
    def get_mission_statistics(self):
        return {
            "waiting": len(self.waiting_queue),
            "assigned": len(self.assigned_missions),
            "completed": len(self.completed_missions),
            "canceled": len(self.canceled_missions)
        }


    # ------------------ 미션 상태 업데이트 ----------------------------

    # 미션 상태 업데이트
    def update_mission_status(self, mission_id: str, status_code: str, status_label: str) -> bool:
        try:
            query = """
                UPDATE missions 
                SET status_code = %s, status_label = %s 
                WHERE mission_id = %s
            """
            self.execute(query, (status_code, status_label, mission_id))
            return True
        except Exception as e:
            print(f"[DB ERROR] 미션 상태 업데이트 중 오류 발생: {e}")
            return False
    
    # 미션 할당 정보 업데이트
    def update_mission_assignment(self, mission_id: str, truck_id: str) -> bool:
        try:
            query = """
                UPDATE missions 
                SET assigned_truck_id = %s, 
                    status_code = 'ASSIGNED',
                    status_label = '트럭 배정됨',
                    timestamp_assigned = %s
                WHERE mission_id = %s
            """
            self.execute(query, (truck_id, datetime.now(), mission_id))
            return True
        except Exception as e:
            print(f"[DB ERROR] 미션 할당 업데이트 중 오류 발생: {e}")
            return False


    # ---------------------- DB 종료 ----------------------------
    
    # DB 연결 종료
    def close(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            print("[DEBUG] DB 연결 종료됨")
        except Exception as e:
            print(f"[ERROR] DB 연결 종료 중 오류 발생: {e}")
    