# backend/mission/manager.py

from collections import deque
from .status import MissionStatus
from .mission import Mission

class MissionManager:
    def __init__(self,db):
        self.db = db
        self.waiting_queue = deque() # 대기 중인 미션들
        self.active_missions = {} # 실행 중인 미션들
        self.completed_missions = {} # 완료된 미션들 
        self.canceled_missions = {} # 취소된 미션들

    def load_from_db(self):
        rows = self.db.load_all_active_and_waiting_missions()
        for row in rows:
            mission = Mission.from_row(row)
            # 대기 중인 미션들
            if mission.status == MissionStatus.WAITING:
                self.waiting_queue.append(mission)
            # 실행 중인 미션들
            else:
                self.active_missions[mission.mission_id] = mission

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