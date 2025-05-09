# backend/mission/mission.py

from datetime import datetime
from typing import Optional, Dict, List
from .status import MissionStatus

class Mission:
    def __init__(self, mission_id: str, cargo_type: str, cargo_amount: float, 
                source: str, destination: str, assigned_truck_id: Optional[str] = None):
        self.mission_id = mission_id
        self.cargo_type = cargo_type
        self.cargo_amount = cargo_amount
        self.source = source
        self.destination = destination
        self.assigned_truck_id = assigned_truck_id
        self.status = MissionStatus.WAITING
        self.timestamp_created = datetime.now()
        self.timestamp_assigned = None
        self.timestamp_completed = None
        
    # 트럭에 미션 할당
    def assign_to_truck(self, truck_id: str) -> None:
        if self.status != MissionStatus.WAITING:
            raise ValueError("대기 중인 미션만 할당 가능합니다")
        self.assigned_truck_id = truck_id
        self.status = MissionStatus.ASSIGNED
        self.timestamp_assigned = datetime.now()
    
    # 미션 완료 처리    
    def complete(self) -> None:
        if self.status not in [MissionStatus.ASSIGNED, MissionStatus.DROPPING_OFF]:
            raise ValueError("할당된 미션만 완료할 수 있습니다")
        self.status = MissionStatus.COMPLETED
        self.timestamp_completed = datetime.now()
    
    # 미션 취소
    def cancel(self) -> None:
        if self.status == MissionStatus.COMPLETED:
            raise ValueError("완료된 미션은 취소할 수 없습니다")
        self.status = MissionStatus.CANCELED
    
    # 미션 상태 업데이트
    def update_status(self, new_status: MissionStatus) -> None:
        if not self._is_valid_status_transition(new_status):
            raise ValueError(f"잘못된 상태 전이: {self.status} -> {new_status}")
        self.status = new_status
        if new_status == MissionStatus.COMPLETED:
            self.timestamp_completed = datetime.now()
    
    # 상태 전이 유효성 검사
    def _is_valid_status_transition(self, new_status: MissionStatus) -> bool:
        valid_transitions = {
            MissionStatus.WAITING: [MissionStatus.ASSIGNED, MissionStatus.CANCELED],
            MissionStatus.ASSIGNED: [
                MissionStatus.EN_ROUTE_TO_PICKUP,
                MissionStatus.CANCELED
            ],
            MissionStatus.EN_ROUTE_TO_PICKUP: [
                MissionStatus.ARRIVED_AT_PICKUP,
                MissionStatus.ERROR
            ],
            MissionStatus.ARRIVED_AT_PICKUP: [
                MissionStatus.PICKING_UP,
                MissionStatus.ERROR
            ],
            MissionStatus.PICKING_UP: [
                MissionStatus.EN_ROUTE_TO_DROPOFF,
                MissionStatus.ERROR
            ],
            MissionStatus.EN_ROUTE_TO_DROPOFF: [
                MissionStatus.ARRIVED_AT_DROPOFF,
                MissionStatus.ERROR
            ],
            MissionStatus.ARRIVED_AT_DROPOFF: [
                MissionStatus.DROPPING_OFF,
                MissionStatus.ERROR
            ],
            MissionStatus.DROPPING_OFF: [
                MissionStatus.COMPLETED,
                MissionStatus.ERROR
            ],
            MissionStatus.ERROR: [MissionStatus.CANCELED],
            MissionStatus.CANCELED: [],
            MissionStatus.COMPLETED: []
        }
        return new_status in valid_transitions.get(self.status, [])
    
    # 딕셔너리 직렬화   
    def to_dict(self) -> Dict:
        return {
            "mission_id": self.mission_id,
            "cargo_type": self.cargo_type,
            "cargo_amount": self.cargo_amount,
            "source": self.source,
            "destination": self.destination,
            "status": {
                "code": self.status.name,
                "label": self.status.value
            },
            "assigned_truck_id": self.assigned_truck_id,
            "timestamp_created": self.timestamp_created.isoformat() if self.timestamp_created else None,
            "timestamp_assigned": self.timestamp_assigned.isoformat() if self.timestamp_assigned else None,
            "timestamp_completed": self.timestamp_completed.isoformat() if self.timestamp_completed else None,
        }
    
    # DB 로우 데이터에서 Mission 객체 생성
    @staticmethod
    def from_row(row) -> 'Mission':
        mission = Mission(
            mission_id=row[0],
            cargo_type=row[1],
            cargo_amount=row[2],
            source=row[3],
            destination=row[4]
        )
        mission.status = MissionStatus[row[5]]
        mission.assigned_truck_id = row[7]
        mission.timestamp_created = row[8]
        mission.timestamp_assigned = row[9]
        mission.timestamp_completed = row[10]
        return mission