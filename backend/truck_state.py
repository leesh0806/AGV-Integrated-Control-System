"""트럭 상태 Enum 및 컨텍스트 클래스 정의"""

from enum import Enum
from datetime import datetime


class TruckState(Enum):
    """트럭의 기본 상태 정의"""
    IDLE = "IDLE"                     # 대기 상태 - 미션 없음
    ASSIGNED = "ASSIGNED"             # 미션 할당됨 (이동 시작 전)
    MOVING = "MOVING"                 # 이동 중
    WAITING = "WAITING"               # 게이트나 작업장에서 대기 중
    LOADING = "LOADING"               # 물건 적재 작업 중
    UNLOADING = "UNLOADING"           # 물건 하역 작업 중
    CHARGING = "CHARGING"             # 충전 중
    EMERGENCY = "EMERGENCY"           # 비상 상태


class MissionPhase(Enum):
    """미션 진행 단계 정의"""
    NONE = "NONE"                      # 미션 없음
    TO_LOADING = "TO_LOADING"          # 적재 장소로 이동 중
    AT_LOADING = "AT_LOADING"          # 적재 장소에 도착
    TO_UNLOADING = "TO_UNLOADING"      # 하역 장소로 이동 중
    AT_UNLOADING = "AT_UNLOADING"      # 하역 장소에 도착
    RETURNING = "RETURNING"            # 대기장소로 복귀 중
    COMPLETED = "COMPLETED"            # 미션 완료


class Direction(Enum):
    """트럭 이동 방향 정의"""
    CLOCKWISE = "CLOCKWISE"              # 시계방향 (정상 흐름)
    COUNTERCLOCKWISE = "COUNTERCLOCKWISE"  # 반시계방향 (비정상 흐름)


class TruckContext:
    """트럭 정보 문맥 클래스"""
    def __init__(self, truck_id):
        self.truck_id = truck_id
        self.state = TruckState.IDLE
        self.position = "STANDBY"      # 현재 물리적 위치
        self.mission_id = None         # 현재 미션 ID
        self.mission_phase = MissionPhase.NONE  # 미션 진행 단계
        self.direction = Direction.CLOCKWISE  # 현재 이동 방향 (기본값: 시계방향)
        self.target_position = None    # 이동 목표 위치
        self.battery_level = 100       # 배터리 잔량 (초기값 100%)
        self.is_charging = False       # 충전 중 여부
        self.last_update_time = datetime.now()  # 마지막 업데이트 시간
        self.gate_status = {}          # 게이트 상태 정보 