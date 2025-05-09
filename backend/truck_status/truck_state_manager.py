from typing import Dict, Optional
from datetime import datetime
from .db import TruckStatusDB

class TruckStatusManager:
    def __init__(self, db: TruckStatusDB):
        self.db = db
        self.trucks: Dict[str, dict] = {}
    
    def get_truck_status(self, truck_id: str) -> dict:
        """트럭의 전체 상태를 가져옴"""
        if truck_id not in self.trucks:
            # DB에서 배터리 상태 조회
            battery_data = self.db.get_latest_battery_status(truck_id)
            if battery_data:
                self.trucks[truck_id] = {
                    "battery": {
                        "level": battery_data['battery_level'],
                        "is_charging": False,
                        "last_updated": battery_data['timestamp']
                    },
                    "position": {
                        "current": "STANDBY",
                        "state": "IDLE",
                        "last_updated": datetime.now()
                    }
                }
            else:
                # DB에 데이터가 없는 경우에만 기본값 사용
                self.trucks[truck_id] = {
                    "battery": {
                        "level": 100,
                        "is_charging": False,
                        "last_updated": datetime.now()
                    },
                    "position": {
                        "current": "STANDBY",
                        "state": "IDLE",
                        "last_updated": datetime.now()
                    }
                }
        return self.trucks[truck_id]
    

    # -------------------------------- 배터리 상태 업데이트 --------------------------------

    # 배터리 상태 업데이트
    def update_battery(self, truck_id: str, level: float, is_charging: bool = None):
        """배터리 상태 업데이트"""
        if not 0 <= level <= 100:
            print(f"[⚠️ 경고] {truck_id}의 배터리 레벨이 유효하지 않음: {level}%")
            level = max(0, min(100, level))
            
        truck = self.get_truck_status(truck_id)
        prev_level = truck["battery"]["level"]
        prev_charging = truck["battery"]["is_charging"]
        
        # 배터리 상태 업데이트
        truck["battery"]["level"] = level
        if is_charging is not None:
            truck["battery"]["is_charging"] = is_charging
        truck["battery"]["last_updated"] = datetime.now()
        
        # 이벤트 타입 결정
        event_type = "BATTERY_UPDATE"
        if truck["battery"]["is_charging"]:
            if level >= 100:
                event_type = "BATTERY_FULL"
            elif level > prev_level:
                event_type = "BATTERY_CHARGING"
            if not prev_charging:
                event_type = "START_CHARGING"
        elif level < prev_level:
            event_type = "BATTERY_DRAINING"
            if prev_charging:
                event_type = "FINISH_CHARGING"
        
        # 상태 메시지 생성
        level_change = level - prev_level
        level_change_str = f"{level_change:+.1f}%" if level_change != 0 else "0%"
        status_msg = f"{level}% ({level_change_str})"
        if truck["battery"]["is_charging"]:
            status_msg += " [충전중]"
        
        print(f"[🔋 배터리 상태] {truck_id}: {status_msg} (충전상태: {prev_charging} -> {truck['battery']['is_charging']})")
        
        # DB에 로깅
        self.db.log_battery_status(
            truck_id=truck_id,
            battery_level=truck["battery"]["level"],
            truck_state="CHARGING" if truck["battery"]["is_charging"] else "NORMAL",
            event_type=event_type
        )
    
    
    # -------------------------------- 위치 상태 업데이트 --------------------------------

    # 위치 상태 업데이트
    def update_position(self, truck_id: str, current: str, state: str):
        """위치 상태 업데이트"""
        truck = self.get_truck_status(truck_id)
        prev_state = truck["position"]["state"]
        
        truck["position"]["current"] = current
        truck["position"]["state"] = state
        truck["position"]["last_updated"] = datetime.now()
        
        print(f"[📍 위치 상태] {truck_id}: {current} (상태: {prev_state} -> {state})")


    # -------------------------------- 조회 --------------------------------
    
    # 모든 트럭의 상태 조회
    def get_all_trucks(self) -> Dict[str, dict]:
        """모든 트럭의 상태 조회"""
        return self.trucks
    
    # 배터리 히스토리 조회
    def get_battery_history(self, truck_id: str, limit: int = 100):
        """배터리 히스토리 조회"""
        return self.db.get_battery_history(truck_id, limit)
    
    # 위치 히스토리 조회
    def get_position_history(self, truck_id: str, limit: int = 100):
        """위치 히스토리 조회"""
        return self.db.get_position_history(truck_id, limit)
    
    # 리소스 정리
    def close(self):
        """리소스 정리"""
        self.db.close() 