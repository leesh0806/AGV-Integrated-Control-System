# backend/serialio/gate_controller.py

class GateController:
    def __init__(self, serial_manager):
        self.serial_manager = serial_manager

    def open_gate(self, gate_id: str):
        cmd = f"{gate_id}_OPEN"
        print(f"[🔓 게이트 열기 요청] → {gate_id}")
        self.serial_manager.send_command(gate_id, "OPEN")
        response = self.serial_manager.read_response(gate_id)
        success = response and response.startswith(f"ACK:{gate_id}_OPENED")
        if success:
            print(f"[✅ 게이트 열림 명령 전송 성공] {gate_id}")
        else:
            print(f"[❌ 게이트 열림 명령 전송 실패] {gate_id}")
        return success

    def close_gate(self, gate_id: str):
        cmd = f"{gate_id}_CLOSE"
        print(f"[🔒 게이트 닫기 요청] → {gate_id}")
        self.serial_manager.send_command(gate_id, "CLOSE")
        response = self.serial_manager.read_response(gate_id)
        success = response and response.startswith(f"ACK:{gate_id}_CLOSED")
        if success:
            print(f"[✅ 게이트 닫힘 명령 전송 성공] {gate_id}")
        else:
            print(f"[❌ 게이트 닫힘 명령 전송 실패] {gate_id}")
        return success
