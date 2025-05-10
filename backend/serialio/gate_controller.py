# backend/serialio/gate_controller.py

import time

class GateController:
    def __init__(self, serial_interface):
        self.serial_interface = serial_interface
        self.gate_states = {
            "GATE_A": "CLOSED",
            "GATE_B": "CLOSED"
        }
        self.operations_in_progress = {}
        self.current_gate_id = None  # 현재 작업 중인 게이트 ID
        
    # SerialInterface 호환 메서드
    def write(self, cmd: str):
        """SerialInterface와 호환되는 write 메서드"""
        if cmd.upper() == "OPEN":
            return self.open_gate(self.current_gate_id)
        elif cmd.upper() == "CLOSE":
            return self.close_gate(self.current_gate_id)
        else:
            print(f"[GateController] Unknown command: {cmd}")
            self.serial_interface.write(cmd)
            return True
    
    def read_response(self, timeout=5):
        """SerialInterface와 호환되는 read_response 메서드"""
        return self.serial_interface.read_response(timeout=timeout)
    
    def close(self):
        """SerialInterface와 호환되는 close 메서드"""
        # 공유 인터페이스를 사용하므로 여기서 닫지 않음
        # 실제 닫기는 DeviceManager에서 담당
        pass
        
    def send_command(self, gate_id: str, action: str):
        """게이트에 명령 전송"""
        self.current_gate_id = gate_id  # 현재 게이트 ID 저장
        if action.upper() == "OPEN":
            return self.open_gate(gate_id)
        elif action.upper() == "CLOSE":
            return self.close_gate(gate_id)
        else:
            print(f"[GateController] Unknown action: {action}")
            return False

    # 응답이 성공을 나타내는지 확인하는 헬퍼 메소드
    def _is_success_response(self, response, gate_id, action):
        """
        응답이 성공을 나타내는지 확인
        
        Args:
            response: 응답 문자열
            gate_id: 게이트 ID ("GATE_A", "GATE_B")
            action: 동작 ("OPEN" 또는 "CLOSE")
            
        Returns:
            bool: 성공 여부
        """
        if not response:
            return False
            
        # 게이트 ID와 letter만 추출 (GATE_A -> A, GATE_B -> B)
        gate_letter = gate_id[-1] if gate_id and len(gate_id) > 0 else ""
        
        # 표준 응답 형식 확인 (ACK:GATE_X_ACTION)
        if action.upper() == "OPEN":
            # 열림 성공 응답 확인
            if response.startswith(f"ACK:{gate_id}_OPENED"):
                return True
            elif response.startswith("GATE_OPENED:"):
                return True
            elif f"게이트{gate_letter}" in response and "열림" in response:
                return True
            elif f"게이트 {gate_letter}" in response and "열림" in response:
                return True
            elif "🔓" in response and f"{gate_letter}" in response:
                return True
        elif action.upper() == "CLOSE":
            # 닫힘 성공 응답 확인
            if response.startswith(f"ACK:{gate_id}_CLOSED"):
                return True
            elif response.startswith("GATE_CLOSED:"):
                return True
            elif f"게이트{gate_letter}" in response and "닫힘" in response:
                return True
            elif f"게이트 {gate_letter}" in response and "닫힘" in response:
                return True
            elif "🔒" in response and f"{gate_letter}" in response:
                return True
                
        return False

    def open_gate(self, gate_id: str):
        if not gate_id:
            print(f"[⚠️ 게이트 ID 누락] 게이트 ID가 지정되지 않았습니다.")
            return False
            
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
        
        # 게이트 ID를 저장(응답 확인용)
        self.current_gate_id = gate_id
        
        # 명령 전송 - 단순 "OPEN" 대신 게이트 ID를 포함한 명령 전송
        self.serial_interface.write(f"{gate_id}_OPEN")
        
        # 응답 대기 (가상 시리얼 지연 시간(3초)보다 훨씬 길게 설정)
        print(f"[🕒 게이트 열림 대기 중] {gate_id} - 최대 15초 대기")
        response = self.serial_interface.read_response(timeout=15)
        
        # 응답 확인 - 개선된 로직 사용
        success = self._is_success_response(response, gate_id, "OPEN")
        
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
        if not gate_id:
            print(f"[⚠️ 게이트 ID 누락] 게이트 ID가 지정되지 않았습니다.")
            return False
            
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
        
        # 게이트 ID를 저장(응답 확인용)
        self.current_gate_id = gate_id
        
        # 명령 전송 - 단순 "CLOSE" 대신 게이트 ID를 포함한 명령 전송
        self.serial_interface.write(f"{gate_id}_CLOSE")
        
        # 응답 대기 (가상 시리얼 지연 시간(2초)보다 훨씬 길게 설정)
        print(f"[🕒 게이트 닫힘 대기 중] {gate_id} - 최대 10초 대기")
        response = self.serial_interface.read_response(timeout=10)
        
        # 응답 확인 - 개선된 로직 사용
        success = self._is_success_response(response, gate_id, "CLOSE")
        
        # 결과 처리
        if success:
            print(f"[✅ 게이트 닫힘 완료] {gate_id}")
            self.gate_states[gate_id] = "CLOSED"
        else:
            print(f"[❌ 게이트 닫힘 실패] {gate_id} - 응답: {response}")
        
        # 작업 완료 표시
        self.operations_in_progress[gate_id] = False
        return success
