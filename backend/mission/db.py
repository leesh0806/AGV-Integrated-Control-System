# backend/mission/db.py

import mysql.connector
from .mission import Mission

class MissionDB:
    def __init__(self, host, user, password, database):
        self.conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
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
        except mysql.connector.Error as err:
            print(f"[DB 오류] {err}")
            self.conn.rollback()


    def load_all_active_and_waiting_missions(self):
        self.cursor.execute("""
        SELECT * FROM missions
        WHERE status_code NOT IN ('COMPLETED', 'CANCELED')
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
    
    def load_all_waiting_missions(self):
        self.cursor.execute("""
        SELECT * FROM missions
        WHERE status_code = 'WAITING'
        """)
        return self.cursor.fetchall()
    
    def load_all_missions(self):
        self.conn.ping(reconnect=True)
        self.cursor.execute("SELECT * FROM missions ORDER BY timestamp_created DESC")
        return self.cursor.fetchall()
    
    def close(self):
        self.cursor.close()
        self.conn.close()