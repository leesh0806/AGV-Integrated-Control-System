from typing import Dict, Optional
from datetime import datetime
from .battery import Battery
from .db import BatteryDB

class BatteryManager:
    def __init__(self, db: BatteryDB):
        self.db = db
        self.batteries: Dict[str, Battery] = {}
    
    def get_battery(self, truck_id: str) -> Battery:
        """트럭의 배터리 객체를 가져옴"""
        if truck_id not in self.batteries:
            self.batteries[truck_id] = Battery(
                truck_id=truck_id,
                level=100,  # 기본값
                last_updated=datetime.now()
            )
        return self.batteries[truck_id]
    
    def update_battery(self, truck_id: str, level: float, is_charging: bool = None):
        """배터리 상태 업데이트"""
        if not 0 <= level <= 100:
            print(f"[⚠️ 경고] {truck_id}의 배터리 레벨이 유효하지 않음: {level}%")
            level = max(0, min(100, level))  # 0-100 사이로 제한
            
        battery = self.get_battery(truck_id)
        prev_level = battery.level
        prev_charging = battery.is_charging
        
        # 배터리 레벨과 충전 상태 업데이트
        battery.update_level(level, is_charging)
        
        # 이벤트 타입 결정
        event_type = "BATTERY_UPDATE"
        if battery.is_charging:
            if level >= 100:
                event_type = "BATTERY_FULL"
            elif level > prev_level:
                event_type = "BATTERY_CHARGING"
        elif level < prev_level:
            event_type = "BATTERY_DRAINING"
        
        # 배터리 레벨 변화량 계산
        level_change = level - prev_level
        level_change_str = f"{level_change:+.1f}%" if level_change != 0 else "0%"
        
        # 상태 메시지 생성
        status_msg = f"{level}% ({level_change_str})"
        if battery.is_charging:
            status_msg += " [충전중]"
        
        print(f"[🔋 배터리 상태] {truck_id}: {status_msg} (충전상태: {prev_charging} -> {battery.is_charging})")
        
        # DB에 로깅
        self.db.log_battery_status(
            truck_id=truck_id,
            battery_level=battery.level,
            truck_state="CHARGING" if battery.is_charging else "NORMAL",
            event_type=event_type
        )
    
    def start_charging(self, truck_id: str):
        """충전 시작"""
        battery = self.get_battery(truck_id)
        battery.is_charging = True
        print(f"[🔌 충전 시작] {truck_id} (현재 배터리: {battery.level}%)")
        self.db.log_battery_status(
            truck_id=truck_id,
            battery_level=battery.level,
            truck_state="CHARGING",
            event_type="START_CHARGING"
        )
    
    def finish_charging(self, truck_id: str):
        """충전 완료"""
        battery = self.get_battery(truck_id)
        battery.is_charging = False
        print(f"[✅ 충전 완료] {truck_id} (최종 배터리: {battery.level}%)")
        self.db.log_battery_status(
            truck_id=truck_id,
            battery_level=battery.level,
            truck_state="NORMAL",
            event_type="FINISH_CHARGING"
        )
    
    def get_all_batteries(self) -> Dict[str, Battery]:
        """모든 배터리 상태 반환"""
        return self.batteries
    
    def get_battery_history(self, truck_id: str, limit: int = 100):
        """배터리 히스토리 조회"""
        return self.db.get_battery_history(truck_id, limit)

    def close(self):
        """리소스 정리"""
        self.db.close() 