# backend/truck_fsm/truck_message_handler.py

from typing import TYPE_CHECKING
import time
if TYPE_CHECKING:
    from .truck_fsm_manager import TruckFSMManager
    from ..truck_status.truck_status_manager import TruckStatusManager


class TruckMessageHandler:
    def __init__(self, truck_fsm_manager: 'TruckFSMManager'):
        self.truck_fsm_manager = truck_fsm_manager
        self.truck_status_manager = None

    def set_status_manager(self, truck_status_manager: 'TruckStatusManager'):
        self.truck_status_manager = truck_status_manager

    def handle_message(self, msg: dict):
        sender = msg.get("sender")
        cmd = msg.get("cmd", "").strip().upper()
        payload = msg.get("payload", {})

        print(f"[📨 TruckMessageHandler] sender={sender}, cmd={cmd}")

        # 트럭 상태 업데이트
        if self.truck_status_manager and cmd == "STATUS_UPDATE":
            self._handle_status_update(sender, payload)
            return
        
        # ACK_GATE_OPENED는 우선 처리
        if cmd == "ACK_GATE_OPENED":
            self.truck_fsm_manager.handle_trigger(sender, "ACK_GATE_OPENED", payload)
            return

        # FSM 트리거 처리
        self.truck_fsm_manager.handle_trigger(sender, cmd, payload)

        if not sender:
            print("[MessageHandler] sender가 없음")
            return

        if cmd == "ARRIVED":
            position = payload.get("position", "UNKNOWN")
            trigger = f"ARRIVED_AT_{position.upper()}"
            self.truck_fsm_manager.handle_trigger(sender, trigger, payload)

        elif cmd == "OBSTACLE":
            self.truck_fsm_manager.handle_trigger(sender, "OBSTACLE", payload)

        elif cmd == "ERROR":
            self.truck_fsm_manager.handle_trigger(sender, "EMERGENCY_TRIGGERED", payload)

        elif cmd == "RESET":
            self.truck_fsm_manager.handle_trigger(sender, "RESET", payload)

        elif cmd == "ASSIGN_MISSION":
            self.truck_fsm_manager.handle_trigger(sender, "ASSIGN_MISSION", payload)

        elif cmd == "START_LOADING":
            self.truck_fsm_manager.handle_trigger(sender, "START_LOADING", payload)

        elif cmd == "FINISH_LOADING":
            self.truck_fsm_manager.handle_trigger(sender, "FINISH_LOADING", payload)

        elif cmd == "START_UNLOADING":
            self.truck_fsm_manager.handle_trigger(sender, "START_UNLOADING", payload)

        elif cmd == "FINISH_UNLOADING":
            self.truck_fsm_manager.handle_trigger(sender, "FINISH_UNLOADING", payload)

        elif cmd == "FINISH_CHARGING":
            self.truck_fsm_manager.handle_trigger(sender, "FINISH_CHARGING", payload)
            return

        elif cmd == "HELLO":
            # HELLO 명령은 트럭 등록을 위한 초기 명령이므로 무시
            print(f"[MessageHandler] 트럭 등록 확인: {sender}")
            return

        else:
            print(f"[MessageHandler] 알 수 없는 명령: {cmd}")
            
    def _handle_status_update(self, truck_id: str, payload: dict):
        """
        STATUS_UPDATE 명령 처리
        
        Args:
            truck_id (str): 트럭 ID
            payload (dict): 상태 정보를 담은 페이로드
        """
        # 타임스탬프 확인
        timestamp = payload.get("timestamp", time.time())
        
        # 배터리 상태 업데이트
        battery_data = payload.get("battery", {})
        if battery_data:
            level = battery_data.get("level", 0)
            is_charging = battery_data.get("is_charging", False)
            self.truck_status_manager.update_battery(truck_id, level, is_charging)
        
        # 위치 정보만 업데이트 (상태는 FSM에서 관리)
        position_data = payload.get("position", {})
        if position_data:
            current = position_data.get("current", "UNKNOWN")
            # 현재 트럭 상태를 유지
            current_status = self.truck_status_manager.get_truck_status(truck_id)
            current_state = current_status["position"]["status"]
            
            # 위치만 업데이트하고 상태는 업데이트하지 않음
            self.truck_status_manager.update_position(truck_id, current, current_state)
            
            # 새로운 위치에 도착했을 때 트리거 생성
            if current:
                trigger = f"ARRIVED_AT_{current.upper()}"
                # 트리거 핸들러 호출 (특수 위치에 도착했을 경우)
                self.truck_fsm_manager.handle_trigger(truck_id, trigger, {})
                
        print(f"[✅ 상태 업데이트 완료] {truck_id}: {payload}")