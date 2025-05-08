# backend/serialio/gate_controller.py

import time

class GateController:
    def __init__(self, serial_manager):
        self.serial_manager = serial_manager
        self.gate_states = {
            "GATE_A": "CLOSED",
            "GATE_B": "CLOSED"
        }
        self.operations_in_progress = {}

    def open_gate(self, gate_id: str):
        # 이미 열려있거나 작업이 진행 중인 경우 무시
        if self.gate_states.get(gate_id) == "OPENED":
            print(f"[⚠️ 게이트 이미 열림] {gate_id}는 이미 열려 있습니다.")
            return True
        
        if gate_id in self.operations_in_progress and self.operations_in_progress[gate_id]:
            print(f"[⚠️ 게이트 작업 중] {gate_id}에 대한 작업이 이미 진행 중입니다.")
            return False
        
        # 작업 시작 표시
        self.operations_in_progress[gate_id] = True
        print(f"[🔓 게이트 열기 요청] → {gate_id}")
        
        # 명령 전송
        self.serial_manager.send_command(gate_id, "OPEN")
        
        # 응답 대기 (가상 시리얼 지연 시간(3초)보다 훨씬 길게 설정)
        print(f"[🕒 게이트 열림 대기 중] {gate_id} - 최대 15초 대기")
        response = self.serial_manager.read_response(facility=gate_id, timeout=15)
        success = response and response.startswith(f"ACK:{gate_id}_OPENED")
        
        # 결과 처리
        if success:
            print(f"[✅ 게이트 열림 완료] {gate_id}")
            self.gate_states[gate_id] = "OPENED"
        else:
            print(f"[❌ 게이트 열림 실패] {gate_id} - 응답: {response}")
        
        # 작업 완료 표시
        self.operations_in_progress[gate_id] = False
        return success

    def close_gate(self, gate_id: str):
        # 이미 닫혀있거나 작업이 진행 중인 경우 무시
        if self.gate_states.get(gate_id) == "CLOSED":
            print(f"[⚠️ 게이트 이미 닫힘] {gate_id}는 이미 닫혀 있습니다.")
            return True
        
        if gate_id in self.operations_in_progress and self.operations_in_progress[gate_id]:
            print(f"[⚠️ 게이트 작업 중] {gate_id}에 대한 작업이 이미 진행 중입니다.")
            return False
        
        # 작업 시작 표시
        self.operations_in_progress[gate_id] = True
        print(f"[🔒 게이트 닫기 요청] → {gate_id}")
        
        # 명령 전송
        self.serial_manager.send_command(gate_id, "CLOSE")
        
        # 응답 대기 (가상 시리얼 지연 시간(2초)보다 훨씬 길게 설정)
        print(f"[🕒 게이트 닫힘 대기 중] {gate_id} - 최대 10초 대기")
        response = self.serial_manager.read_response(facility=gate_id, timeout=10)
        success = response and response.startswith(f"ACK:{gate_id}_CLOSED")
        
        # 결과 처리
        if success:
            print(f"[✅ 게이트 닫힘 완료] {gate_id}")
            self.gate_states[gate_id] = "CLOSED"
        else:
            print(f"[❌ 게이트 닫힘 실패] {gate_id} - 응답: {response}")
        
        # 작업 완료 표시
        self.operations_in_progress[gate_id] = False
        return success
