# backend/fsm/message_handler.py

from .state_machine import TruckFSMManager

class MessageHandler:
    def __init__(self, fsm_manager):
        self.fsm_manager = fsm_manager
        self.status_manager = None

    def set_status_manager(self, status_manager):
        self.status_manager = status_manager

    def handle_message(self, msg: dict):
        truck_id = msg.get("sender")
        cmd = msg.get("cmd", "").strip().upper()
        payload = msg.get("payload", {})

        if not truck_id:
            print("[MessageHandler] sender가 없음")
            return

        if cmd == "ARRIVED":
            position = payload.get("position", "UNKNOWN")
            trigger = f"ARRIVED_AT_{position.upper()}"
            self.fsm_manager.handle_trigger(truck_id, trigger, payload)

        elif cmd == "OBSTACLE":
            self.fsm_manager.handle_trigger(truck_id, "OBSTACLE", payload)

        elif cmd == "ERROR":
            self.fsm_manager.handle_trigger(truck_id, "EMERGENCY_TRIGGERED", payload)

        elif cmd == "RESET":
            self.fsm_manager.handle_trigger(truck_id, "RESET", payload)

        elif cmd == "ASSIGN_MISSION":
            self.fsm_manager.handle_trigger(truck_id, "ASSIGN_MISSION", payload)

        elif cmd == "ACK_GATE_OPENED":
            self.fsm_manager.handle_trigger(truck_id, "ACK_GATE_OPENED", payload)

        elif cmd == "START_LOADING":
            self.fsm_manager.handle_trigger(truck_id, "START_LOADING", payload)

        elif cmd == "FINISH_LOADING":
            self.fsm_manager.handle_trigger(truck_id, "FINISH_LOADING", payload)

        elif cmd == "START_UNLOADING":
            self.fsm_manager.handle_trigger(truck_id, "START_UNLOADING", payload)

        elif cmd == "FINISH_UNLOADING":
            self.fsm_manager.handle_trigger(truck_id, "FINISH_UNLOADING", payload)

        elif cmd == "BATTERY_LEVEL":
            level = payload.get("level")
            print(f"[트럭 {truck_id}] 배터리 상태: {level}%")
            if self.status_manager:
                self.status_manager.update_battery(truck_id, level)
            return

        elif cmd == "FINISH_CHARGING":
            self.fsm_manager.handle_trigger(truck_id, "FINISH_CHARGING", payload)
            return

        elif cmd == "HELLO":
            # HELLO 명령은 트럭 등록을 위한 초기 명령이므로 무시
            print(f"[MessageHandler] 트럭 등록 확인: {truck_id}")
            return

        else:
            print(f"[MessageHandler] 알 수 없는 명령: {cmd}")