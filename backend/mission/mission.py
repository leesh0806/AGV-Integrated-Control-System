# backend/mission/mission.py

from datetime import datetime
from .status import MissionStatus

class Mission:
    def __init__(self, mission_id, cargo_type, cargo_amount, source, destination, truck_id=None):
        self.mission_id = mission_id
        self.cargo_type = cargo_type
        self.cargo_amount = cargo_amount
        self.source = source
        self.destination = destination
        self.assigned_truck_id = truck_id

        self.status = MissionStatus.WAITING

        self.timestamp_created = datetime.now()
        self.timestamp_assigned = None
        self.timestamp_completed = None

    def assign_to_truck(self, truck_id):
        self.assigned_truck_id = truck_id
        self.status = MissionStatus.ASSIGNED
        self.timestamp_assigned = datetime.now()

    def update_status(self, new_status):
        # ✅ 문자열이 들어올 경우 Enum으로 변환
        if isinstance(new_status, str):
            new_status = MissionStatus[new_status]
        self.status = new_status
        if new_status == MissionStatus.COMPLETED:
            self.timestamp_completed = datetime.now()


    def cancel(self):
        self.status = MissionStatus.CANCELED

    def to_dict(self):
        return {
            "mission_id": self.mission_id,
            "cargo_type": self.cargo_type,
            "cargo_amount": self.cargo_amount,
            "source": self.source,
            "destination": self.destination,
            "status": {
                "code": self.status.name, # ex. "DROPPING_OFF"
                "label": self.status.value # ex. "하차중"
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