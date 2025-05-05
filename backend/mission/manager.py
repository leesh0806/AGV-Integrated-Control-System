# backend/mission/manager.py

from collections import deque
from .status import MissionStatus
from .mission import Mission
from backend.mission.db import MissionDB

class MissionManager:
    def __init__(self,db):
        self.db = db
        self.waiting_queue = deque() # 대기 중인 미션들
        self.active_missions = {} # 실행 중인 미션들
        self.completed_missions = {} # 완료된 미션들 
        self.canceled_missions = {} # 취소된 미션들

    def load_from_db(self):
        # 커넥션을 새로 생성
        db = MissionDB(host="localhost", user="root", password="jinhyuk2dacibul", database="dust")

        # WAITING 미션 불러오기
        rows = db.load_all_waiting_missions()
        print(f"[DEBUG] DB에서 WAITING 미션 {len(rows)}개 불러옴")
        self.waiting_queue.clear()
        self.active_missions.clear()
        for row in rows:
            mission = Mission.from_row(row)
            self.waiting_queue.append(mission)

        # ASSIGNED 미션 불러오기
        assigned_rows = db.load_all_assigned_missions()
        print(f"[DEBUG] DB에서 ASSIGNED 미션 {len(assigned_rows)}개 불러옴")
        for row in assigned_rows:
            mission = Mission.from_row(row)
            mission.cancel()
            self.canceled_missions[mission.mission_id] = mission
            db.save_mission(mission)
            
        db.close()

    def add_mission(self, mission):
        self.waiting_queue.append(mission)
        self.db.save_mission(mission)

    def complete_mission(self, mission_id):
        if mission_id in self.active_missions:
            mission = self.active_missions.pop(mission_id)
            mission.update_status(MissionStatus.COMPLETED)
            self.completed_missions[mission_id] = mission
            self.db.save_mission(mission)

    def cancel_mission(self, mission_id):
        if mission_id in self.active_missions:
            mission = self.active_missions.pop(mission_id)
            mission.cancel()
            self.canceled_missions[mission_id] = mission
            self.db.save_mission(mission)
            return
        
        for mission in list(self.waiting_queue):
            if mission.mission_id == mission_id:
                self.waiting_queue.remove(mission)
                mission.cancel()
                self.canceled_missions[mission_id] = mission
                self.db.save_mission(mission)
                return
            
    def assign_next_to_truck(self, truck_id):
        if self.waiting_queue:
            mission = self.waiting_queue.popleft()
            mission.assign_to_truck(truck_id)
            self.active_missions[mission.mission_id] = mission
            self.db.save_mission(mission)
            return mission
        return None
    
    def get_mission_by_truck(self, truck_id):
        for mission in self.active_missions.values():
            if mission.assigned_truck_id == truck_id:
                return mission
        return None

    def save_to_db(self):
        for mission in self.missions:
            if mission.status_code == "COMPLETED" and mission.timestamp_completed:
                self.db.update_mission_completion(
                    mission_id = mission.mission_id,
                    status_code="COMPLETED",
                    status_label="완료됨",
                    timestamp_completed=mission.timestamp_completed
                )