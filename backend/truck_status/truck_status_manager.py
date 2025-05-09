from typing import Dict, Optional
from datetime import datetime
from .truck_status_db import TruckStatusDB

class TruckStatusManager:
    def __init__(self, db: TruckStatusDB):
        self.truck_status_db = db
        self.truck_status = {}
    
    # -------------------------------- 트럭 상태 조회 --------------------------------
    def get_truck_status(self, truck_id: str) -> dict:
        if truck_id not in self.truck_status:
            # 배터리 정보 조회
            battery_data = self.truck_status_db.get_latest_battery_status(truck_id)
            position_data = self.truck_status_db.get_latest_position_status(truck_id)

            # 배터리 초기화
            battery_status = {
                "level": 100.0,
                "is_charging": False
            }
            if battery_data:
                battery_status = {
                    "level": battery_data["battery_level"],
                    "is_charging": battery_data["event_type"] == "CHARGING_START"
                }

            # 위치 초기화
            position_status = {
                "location": "UNKNOWN",
                "status": "IDLE"
            }
            if position_data:
                position_status = {
                    "location": position_data["location"],
                    "status": position_data["status"]
                }

            # 트럭 상태 초기화
            self.truck_status[truck_id] = {
                "battery": battery_status,
                "position": position_status
            }

        return self.truck_status[truck_id]
    
    # -------------------------------- 배터리 상태 업데이트 --------------------------------

    def update_battery(self, truck_id: str, level: float, is_charging: bool):
        """배터리 상태 업데이트"""
        truck = self.get_truck_status(truck_id)
        prev_level = truck["battery"]["level"]
        prev_charging = truck["battery"]["is_charging"]
        
        # 배터리 레벨 업데이트
        truck["battery"]["level"] = level
        truck["battery"]["is_charging"] = is_charging
        
        # 상태 변화 로깅
        level_change_str = f"{prev_level:.1f}% → {level:.1f}%"
        status_msg = f"{level}% ({level_change_str})"
        
        if is_charging:
            status_msg += " [충전중]"
            
        print(f"[🔋 배터리 상태] {truck_id}: {status_msg} (충전상태: {prev_charging} -> {truck['battery']['is_charging']})")
        
        # DB에 로깅
        self.truck_status_db.log_battery_status(
            truck_id=truck_id,
            battery_level=level,
            truck_status="CHARGING" if truck["battery"]["is_charging"] else "NORMAL",
            event_type="CHARGING_START" if is_charging else "CHARGING_END"
        )
    
    # -------------------------------- 위치 상태 업데이트 --------------------------------

    def update_position(self, truck_id: str, current: str, status: str):
        """위치 상태 업데이트"""
        truck = self.get_truck_status(truck_id)
        prev_status = truck["position"]["status"]
        
        # TruckState 열거형을 문자열로 변환
        if hasattr(status, 'name'):
            status_str = status.name
        elif hasattr(status, 'value'):
            status_str = status.value
        else:
            status_str = str(status)
        
        # 위치 정보 업데이트
        truck["position"]["location"] = current
        truck["position"]["status"] = status_str
        
        # 상태 변화 로깅
        print(f"[📍 위치 상태] {truck_id}: {current} (상태: {prev_status} -> {status_str})")
        
        # DB에 로깅
        self.truck_status_db.log_position_status(truck_id, current, status_str)

    # -------------------------------- 조회 --------------------------------
    
    def get_all_trucks(self) -> Dict[str, dict]:
        """모든 트럭의 상태 조회"""
        return self.truck_status
    
    def get_battery_history(self, truck_id: str, limit: int = 100):
        """배터리 히스토리 조회"""
        return self.truck_status_db.get_battery_history(truck_id, limit)
    
    def get_position_history(self, truck_id: str, limit: int = 100):
        """위치 히스토리 조회"""
        return self.truck_status_db.get_position_history(truck_id, limit)
    
    def close(self):
        """리소스 정리"""
        self.truck_status_db.close()
        print("[DEBUG] TruckStatusManager 리소스 정리 완료")
