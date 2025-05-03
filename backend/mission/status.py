# backend/mission/status.py

from enum import Enum

class MissionStatus(Enum):
    WAITING = "대기중"
    ASSIGNED = "트럭 배정됨"
    EN_ROUTE_TO_PICKUP = "적재지로 이동중"
    ARRIVED_AT_PICKUP = "적재지 도착"
    PICKING_UP = "적재중"
    EN_ROUTE_TO_DROPOFF = "하차지로 이동중"
    ARRIVED_AT_DROPOFF = "하차지 도착"
    DROPPING_OFF = "하차중"
    COMPLETED = "완료됨"
    CANCELED = "취소됨"
    ERROR = "오류"