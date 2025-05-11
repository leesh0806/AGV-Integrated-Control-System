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


class TruckContext:
    """트럭 정보 문맥 클래스"""
    def __init__(self, truck_id):
        self.truck_id = truck_id
        self.state = TruckState.IDLE
        self.position = "STANDBY"      # 현재 물리적 위치
        self.mission_id = None         # 현재 미션 ID
        self.mission_phase = MissionPhase.NONE  # 미션 진행 단계
        self.target_position = None    # 이동 목표 위치
        self.battery_level = 100       # 배터리 잔량
        self.is_charging = False       # 충전 중 여부
        self.last_update_time = datetime.now()  # 마지막 업데이트 시간
        self.gate_status = {}          # 게이트 상태 정보
        
    def update_position(self, new_position):
        """위치 정보 업데이트"""
        old_position = self.position
        self.position = new_position
        self.last_update_time = datetime.now()
        return old_position
        
    def update_state(self, new_state):
        """상태 정보 업데이트"""
        old_state = self.state
        self.state = new_state
        self.last_update_time = datetime.now()
        return old_state
        
    def update_battery(self, level, is_charging):
        """배터리 정보 업데이트"""
        self.battery_level = level
        self.is_charging = is_charging
        self.last_update_time = datetime.now() 