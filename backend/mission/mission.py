# backend/mission/mission.py

"""
이 Mission 클래스는 자율 운송 시스템에서 트럭에게 부여되는 미션(작업)의 데이터 구조를 표현하는 객체입니다. 
상태 업데이트, 시간 기록, DB-객체 변환, 딕셔너리 직렬화를 담당합니다.
"""

from datetime import datetime
from .status import MissionStatus

class Mission:
    def __init__(self, mission_id, cargo_type, cargo_amount, source, destination, truck_id=None):
        self.mission_id = mission_id # 미션 ID
        self.cargo_type = cargo_type # 화물 타입
        self.cargo_amount = cargo_amount # 화물 양
        self.source = source # 출발지
        self.destination = destination # 도착지
        self.assigned_truck_id = truck_id # 할당된 트럭 ID
        self.status = MissionStatus.WAITING # 미션 상태

        self.timestamp_created = datetime.now() # 미션 생성 시간
        self.timestamp_assigned = None # 미션 할당 시간
        self.timestamp_completed = None # 미션 완료 시간

    # 트럭에 미션 할당
    def assign_to_truck(self, truck_id):
        self.assigned_truck_id = truck_id
        self.status = MissionStatus.ASSIGNED
        self.timestamp_assigned = datetime.now()

    # 미션 상태 업데이트
    def update_status(self, new_status):
        if isinstance(new_status, str):
            new_status = MissionStatus[new_status]
        self.status = new_status
        if new_status == MissionStatus.COMPLETED:
            self.timestamp_completed = datetime.now()

    # 미션 취소
    def cancel(self):
        self.status = MissionStatus.CANCELED

    # 딕셔너리 직렬화
    def to_dict(self):
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
            "timestamp_created": str(self.timestamp_created),
            "timestamp_assigned": str(self.timestamp_assigned) if self.timestamp_assigned else None,
            "timestamp_completed": str(self.timestamp_completed) if self.timestamp_completed else None,
        }
    
    @staticmethod
    def from_row(row):
        m = Mission(row[0], row[1], row[2], row[3], row[4])
        m.status = MissionStatus[row[5]]
        m.assigned_truck_id = row[7]
        m.timestamp_created = row[8]
        m.timestamp_assigned = row[9]
        m.timestamp_completed = row[10]
        return m