# backend/mission/manager.py

"""
이 MissionManager 클래스는 자율 운송 시스템의 미션 큐 관리 중심 허브입니다. 
미션(할당된 작업)의 현재 상태를 RAM에서 관리하면서, 변경 사항을 MySQL DB와 동기화하는 역할을 합니다.
"""

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
        """DB에서 미션 로드"""
        self.missions = self.db.load_all_active_and_waiting_missions()
        self.waiting_queue.clear()
        self.active_missions.clear()
        for mission in self.missions:
            if mission.status == MissionStatus.WAITING:
                self.waiting_queue.append(mission)
            elif mission.status == MissionStatus.ASSIGNED:
                mission.update_status(MissionStatus.WAITING)  # ASSIGNED -> WAITING으로 변경
                self.waiting_queue.append(mission)  # waiting_queue에 추가
                self.db.update_mission_status(  # DB 상태 업데이트
                    mission_id=mission.mission_id,
                    status_code="WAITING",
                    status_label="대기중",
                    timestamp_assigned=None,  # 할당 타임스탬프 초기화
                    timestamp_completed=None   # 완료 타임스탬프 초기화
                )

    def get_all_active_and_waiting_missions(self):
        """현재 로드된 모든 활성 및 대기 중인 미션 반환"""
        return self.missions

    # 미션 추가
    def add_mission(self, mission):
        self.waiting_queue.append(mission)
        self.db.save_mission(mission)

    # 미션 완료
    def complete_mission(self, mission_id):
        if mission_id in self.active_missions:
            mission = self.active_missions.pop(mission_id)
            mission.update_status(MissionStatus.COMPLETED)
            self.completed_missions[mission_id] = mission
            self.db.save_mission(mission)

    # 미션 취소
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
            
    # 트럭에 미션 할당
    def assign_next_to_truck(self, truck_id):
        if self.waiting_queue:
            mission = self.waiting_queue.popleft()
            mission.assign_to_truck(truck_id)
            self.active_missions[mission.mission_id] = mission
            self.db.save_mission(mission)
            return mission
        return None
    
    # 트럭에 할당된 미션 조회
    def get_mission_by_truck(self, truck_id):
        for mission in self.active_missions.values():
            if mission.assigned_truck_id == truck_id:
                return mission
        return None

    # 미션 저장
    def save_to_db(self):
        for mission in self.missions:
            if mission.status_code == "COMPLETED" and mission.timestamp_completed:
                self.db.update_mission_completion(
                    mission_id = mission.mission_id,
                    status_code="COMPLETED",
                    status_label="완료됨",
                    timestamp_completed=mission.timestamp_completed
                )