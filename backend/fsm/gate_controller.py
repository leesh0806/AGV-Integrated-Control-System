# backend/fsm/gate_controller.py

class GateController:
    def __init__(self, serial_manager):
        self.serial_manager = serial_manager

    def open_gate(self, gate_id: str) -> bool:
        print(f"[🔓 게이트 열기 요청] → {gate_id}")
        success = self.serial_manager.send_command(gate_id, "OPEN")
        if success:
            print(f"[✅ 게이트 열림 명령 전송 성공] {gate_id}")
        else:
            print(f"[❌ 게이트 열림 명령 전송 실패] {gate_id}")
        return success

    def close_gate(self, gate_id: str) -> bool:
        print(f"[🔒 게이트 닫기 요청] → {gate_id}")
        success = self.serial_manager.send_command(gate_id, "CLOSE")
        if success:
            print(f"[✅ 게이트 닫힘 명령 전송 성공] {gate_id}")
        else:
            print(f"[❌ 게이트 닫힘 명령 전송 실패] {gate_id}")
        return success
