# backend/mission/db.py

import mysql.connector
from .mission import Mission

class MissionDB:
    def __init__(self, host, user, password, database):
        self.db_config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
        self.conn = mysql.connector.connect(**self.db_config)
        self.cursor = self.conn.cursor()

    def save_mission(self, mission: Mission):
        query = """
        INSERT INTO missions (
            mission_id, cargo_type, cargo_amount, source, destination, status_code, status_label, assigned_truck_id,
            timestamp_created, timestamp_assigned, timestamp_completed
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            status_code = VALUES(status_code),
            status_label = VALUES(status_label),
            assigned_truck_id = VALUES(assigned_truck_id),
            timestamp_assigned = VALUES(timestamp_assigned),
            timestamp_completed = VALUES(timestamp_completed)
        """
        try:
            self.conn.ping(reconnect=True)
            self.cursor = self.conn.cursor()
            self.cursor.execute(query, (
                mission.mission_id,
                mission.cargo_type,
                mission.cargo_amount,
                mission.source,
                mission.destination,
                mission.status.name,
                mission.status.value,
                mission.assigned_truck_id,
                mission.timestamp_created,
                mission.timestamp_assigned,
                mission.timestamp_completed
            ))
            self.conn.commit()
            print(f"[DEBUG] 미션 저장 성공: {mission.mission_id}")
        except mysql.connector.Error as err:
            print(f"[DB 오류] 미션 저장 실패: {err}")
            self.conn.rollback()
            raise

    def get_connection(self):
        """새로운 데이터베이스 연결을 생성"""
        try:
            return mysql.connector.connect(**self.db_config)
        except Exception as e:
            print(f"[ERROR] DB 연결 생성 실패: {e}")
            raise

    def load_all_active_and_waiting_missions(self):
        """모든 활성 및 대기 중인 미션을 로드"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            print("[DEBUG] 활성/대기 미션 로드 시작")
            
            # WAITING 상태의 미션만 로드
            query = """
                SELECT * FROM missions 
                WHERE status_code = 'WAITING'
                AND assigned_truck_id IS NULL
                ORDER BY timestamp_created ASC
            """
            print(f"[DEBUG] 실행할 쿼리: {query}")
            
            cursor.execute(query)
            missions = cursor.fetchall()
            
            print(f"[DEBUG] 로드된 미션 수: {len(missions)}")
            if len(missions) > 0:
                print("[DEBUG] 로드된 미션 상세:")
                for mission in missions:
                    print(f"  - 미션ID: {mission[0]}")
                    print(f"    상태: {mission[5]}")
                    print(f"    트럭ID: {mission[6]}")
                    print(f"    생성시간: {mission[8]}")
            
            cursor.close()
            conn.close()
            
            return missions
        except Exception as e:
            print(f"[ERROR] 미션 로드 중 오류 발생: {e}")
            return []
    
    def load_all_waiting_missions(self):
        """대기 중인 모든 미션을 로드"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            print("[DEBUG] 대기 중인 미션 로드 시작")
            
            # 전체 미션 수 확인
            cursor.execute("SELECT COUNT(*) FROM missions")
            total_missions = cursor.fetchone()[0]
            print(f"[DEBUG] 전체 미션 수: {total_missions}")
            
            # WAITING 상태 미션 수 확인
            cursor.execute("SELECT COUNT(*) FROM missions WHERE status_code = 'WAITING'")
            waiting_missions = cursor.fetchone()[0]
            print(f"[DEBUG] WAITING 상태 미션 수: {waiting_missions}")
            
            # 대기 중인 미션 조회
            query = """
            SELECT * FROM missions 
            WHERE status_code = 'WAITING'
            AND assigned_truck_id IS NULL
            ORDER BY timestamp_created ASC
            """
            cursor.execute(query)
            missions = cursor.fetchall()
            
            print(f"[DEBUG] 조회된 대기 미션 수: {len(missions)}")
            if len(missions) > 0:
                print("[DEBUG] 대기 미션 상세:")
                for mission in missions:
                    print(f"  - 미션ID: {mission[0]}")
                    print(f"    상태: {mission[1]}")
                    print(f"    트럭ID: {mission[2]}")
                    print(f"    생성시간: {mission[3]}")
            
            cursor.close()
            conn.close()
            
            return [Mission(*mission) for mission in missions]
            
        except Exception as e:
            print(f"[ERROR] 대기 중인 미션 로드 중 오류 발생: {e}")
            return []
    
    def load_all_assigned_missions(self):
        self.conn.ping(reconnect=True)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
        SELECT * FROM missions
        WHERE UPPER(status_code) = 'ASSIGNED'
        """)
        return self.cursor.fetchall()
    
    def update_mission_completion(self, mission_id, status_code, status_label, timestamp_completed):
        cursor = self.conn.cursor()
        query = """
            UPDATE missions
            SET status_code = %s,
                status_label = %s,
                timestamp_completed = %s
            WHERE mission_id = %s
        """

        cursor.execute(query, (status_code, status_label, timestamp_completed, mission_id))
        self.conn.commit()
    
    def update_mission_status(self, mission_id, status_code, status_label, timestamp_assigned=None, timestamp_completed=None):
        cursor = self.conn.cursor()
        query = """
            UPDATE missions
            SET status_code = %s,
                status_label = %s,
                timestamp_assigned = %s,
                timestamp_completed = %s
            WHERE mission_id = %s
        """

        cursor.execute(query, (status_code, status_label, timestamp_assigned, timestamp_completed, mission_id))
        self.conn.commit()
    
    def load_all_missions(self):
        self.conn.ping(reconnect=True)
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT * FROM missions ORDER BY timestamp_created DESC")
        return self.cursor.fetchall()
    
    def verify_waiting_missions(self, waiting_queue):
        """waiting_queue와 DB의 동기화 상태 확인"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            print("[DEBUG] waiting_queue와 DB 동기화 상태 확인 시작")
            print(f"[DEBUG] waiting_queue 크기: {len(waiting_queue)}")
            
            # DB에서 대기 중인 미션 조회
            query = """
            SELECT mission_id, status_code, assigned_truck_id, timestamp_created 
            FROM missions
            WHERE status_code = 'WAITING'
            AND assigned_truck_id IS NULL
            ORDER BY timestamp_created ASC
            """
            cursor.execute(query)
            db_missions = cursor.fetchall()
            
            print(f"[DEBUG] DB에서 조회된 대기 미션 수: {len(db_missions)}")
            if len(db_missions) > 0:
                print("[DEBUG] DB의 대기 미션 상세:")
                for mission in db_missions:
                    print(f"  - 미션ID: {mission[0]}")
                    print(f"    상태: {mission[1]}")
                    print(f"    트럭ID: {mission[2]}")
                    print(f"    생성시간: {mission[3]}")
            
            # waiting_queue의 미션 ID 조회
            queue_missions = {mission.mission_id for mission in waiting_queue}
            print(f"[DEBUG] waiting_queue의 미션 ID 목록: {queue_missions}")
            
            # DB의 미션 ID 조회
            db_mission_ids = {mission[0] for mission in db_missions}
            print(f"[DEBUG] DB의 미션 ID 목록: {db_mission_ids}")
            
            # 동기화 상태 확인
            only_in_db = db_mission_ids - queue_missions
            only_in_queue = queue_missions - db_mission_ids
            
            if only_in_db:
                print(f"[WARNING] DB에만 있는 미션: {only_in_db}")
            if only_in_queue:
                print(f"[WARNING] waiting_queue에만 있는 미션: {only_in_queue}")
            
            is_synced = not (only_in_db or only_in_queue)
            print(f"[DEBUG] 동기화 상태: {'동기화됨' if is_synced else '동기화되지 않음'}")
            
            cursor.close()
            conn.close()
            
            return is_synced, only_in_db, only_in_queue
            
        except Exception as e:
            print(f"[ERROR] 동기화 상태 확인 중 오류 발생: {e}")
            return False, set(), set()
    
    def close(self):
        self.cursor.close()
        self.conn.close()

    def assign_mission_to_truck(self, mission_id, truck_id):
        """미션을 트럭에 할당"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 트럭 ID 유효성 검사
            if truck_id not in ['TRUCK_01', 'TRUCK_02', 'TRUCK_03']:
                print(f"잘못된 트럭 ID: {truck_id}")
                return False
                
            # 미션 상태 확인
            cursor.execute("SELECT status_code FROM missions WHERE mission_id = %s", (mission_id,))
            result = cursor.fetchone()
            if not result or result[0] in ['COMPLETED', 'CANCELED']:
                print(f"미션 {mission_id}는 할당할 수 없는 상태입니다.")
                return False
            
            # 미션 할당
            query = """
                UPDATE missions 
                SET status_code = 'ASSIGNED',
                    status_label = '트럭 배정됨',
                    assigned_truck_id = %s,
                    timestamp_assigned = NOW()
                WHERE mission_id = %s
                AND status_code NOT IN ('COMPLETED', 'CANCELED')
            """
            cursor.execute(query, (truck_id, mission_id))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return True
        except Exception as e:
            print(f"미션 할당 중 오류 발생: {e}")
            return False