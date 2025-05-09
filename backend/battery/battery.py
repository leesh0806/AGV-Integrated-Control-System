from dataclasses import dataclass
from datetime import datetime

@dataclass
class Battery:
    truck_id: str
    level: float
    last_updated: datetime
    is_charging: bool = False
    
    # 배터리가 30% 이하인지 확인
    @property
    def needs_charging(self) -> bool:
        return self.level <= 30
    
    # 배터리가 100%인지 확인
    @property
    def is_fully_charged(self) -> bool:
        return self.level >= 100
    
    # 배터리 레벨 업데이트
    def update_level(self, new_level: float, is_charging: bool = None):
        self.level = max(0, min(100, new_level))  # 0-100 사이로 제한
        if is_charging is not None:
            self.is_charging = is_charging
            print(f"[DEBUG] 배터리 충전 상태 변경: {self.is_charging}")
        self.last_updated = datetime.now()
        
    # 딕셔너리로 변환
    def to_dict(self):
        return {
            "truck_id": self.truck_id,
            "level": self.level,
            "is_charging": self.is_charging,
            "last_updated": self.last_updated.isoformat()
        } 