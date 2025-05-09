# backend/truck_fsm/truck_message_handler.py

from typing import TYPE_CHECKING
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
        if self.truck_status_manager:
            if cmd == "STATUS_UPDATE":
                pass

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

        elif cmd == "ACK_GATE_OPENED":
            self.truck_fsm_manager.handle_trigger(sender, "ACK_GATE_OPENED", payload)

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