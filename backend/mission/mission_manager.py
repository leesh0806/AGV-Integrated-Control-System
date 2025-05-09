# backend/mission/mission_manager.py

from .mission import Mission
from .mission_status import MissionStatus
from .mission_db import MissionDB
from typing import List, Optional

class MissionManager:
    def __init__(self, db: MissionDB):
        self.db = db
        self.command_sender = None

    # 커맨더 설정
    def set_command_sender(self, command_sender):
        self.command_sender = command_sender

    # 대기 중인 미션 알림
    def _notify_trucks_of_waiting_missions(self) -> None:
        if not self.command_sender:
            return
                
        waiting_missions = self.get_waiting_missions()
        if waiting_missions:
            print(f"[📢 미션 알림] 대기 중인 미션 {len(waiting_missions)}개가 있습니다.")
            for truck_id in self.command_sender.truck_sockets.keys():
                self.command_sender.send(truck_id, "MISSIONS_AVAILABLE", {
                    "count": len(waiting_missions)
                })
    
    # ------------------ 미션 조회 ----------------------------

    # 미션 ID로 미션 조회
    def find_mission_by_id(self, mission_id: str) -> Optional[Mission]:
        """미션 ID로 미션 조회"""
        mission_data = self.db.find_mission_by_id(mission_id)
        if not mission_data:
            return None
        return Mission.from_row(mission_data)
    
    # 트럭 ID로 미션 조회
    def get_missions_by_truck(self, truck_id: str) -> List[Mission]:
        """트럭 ID로 할당된 미션 목록 조회"""
        mission_rows = self.db.get_missions_by_truck(truck_id)
        return [Mission.from_row(row) for row in mission_rows]
    
    # ------------------ 미션 조회 ----------------------------

    # 대기 중인 미션 목록 조회
    def get_waiting_missions(self) -> List[Mission]:
        """대기 중인 미션 목록 조회"""
        mission_rows = self.db.get_waiting_missions()
        return [Mission.from_row(row) for row in mission_rows]
    
    # 할당된 미션과 대기 중인 미션 목록 조회
    def get_assigned_and_waiting_missions(self) -> List[Mission]:
        """할당된 미션과 대기 중인 미션 목록 조회"""
        mission_rows = self.db.get_assigned_and_waiting_missions()
        return [Mission.from_row(row) for row in mission_rows]
    
    # ------------------ 미션 생성 ----------------------------

    # 새 미션 생성
    def create_mission(self, mission_id: str, cargo_type: str, cargo_amount: float,
                      source: str, destination: str) -> Optional[Mission]:
        try:
            mission = Mission(
                mission_id=mission_id,
                cargo_type=cargo_type,
                cargo_amount=cargo_amount,
                source=source,
                destination=destination
            )
            
            mission_data = (
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
            )
            
            if self.db.save_mission(mission_data):
                self._notify_trucks_of_waiting_missions()
                return mission
            return None
        except Exception as e:
            print(f"[ERROR] 미션 생성 실패: {e}")
            return None
    
    # ------------------ 미션 할당 ----------------------------

    # 미션을 트럭에 할당
    def assign_mission_to_truck(self, mission_id: str, truck_id: str) -> bool:
        mission = self.find_mission_by_id(mission_id)
        if not mission:
            return False
            
        try:
            mission.assign_to_truck(truck_id)
            mission_data = (
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
            )
            
            if self.db.save_mission(mission_data):
                return True
            return False
        except ValueError as e:
            print(f"[ERROR] 미션 할당 실패: {e}")
            return False
    
    # ------------------ 미션 완료 ----------------------------

    # 미션 완료 처리
    def complete_mission(self, mission_id: str) -> bool:
        mission = self.find_mission_by_id(mission_id)
        if not mission:
            return False
            
        try:
            mission.complete()
            mission_data = (
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
            )
            
            return self.db.save_mission(mission_data)
        except ValueError as e:
            print(f"[ERROR] 미션 완료 처리 실패: {e}")
            return False
    
    # ------------------ 미션 취소 ----------------------------

    # 미션 취소
    def cancel_mission(self, mission_id: str) -> bool:
        mission = self.find_mission_by_id(mission_id)
        if not mission:
            return False
            
        try:
            mission.cancel()
            mission_data = (
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
            )
            
            if self.db.save_mission(mission_data):
                self._notify_trucks_of_waiting_missions()
                return True
            return False
        except ValueError as e:
            print(f"[ERROR] 미션 취소 실패: {e}")
            return False
    
    # ------------------ 미션 상태 업데이트 ----------------------------

    # 미션 상태 업데이트
    def update_mission_status(self, mission_id: str, new_status: MissionStatus) -> bool:
        mission = self.find_mission_by_id(mission_id)
        if not mission:
            return False
            
        try:
            mission.update_status(new_status)
            mission_data = (
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
            )
            
            if self.db.save_mission(mission_data):
                if new_status == MissionStatus.WAITING:
                    self._notify_trucks_of_waiting_missions()
                return True
            return False
        except ValueError as e:
            print(f"[ERROR] 미션 상태 업데이트 실패: {e}")
            return False