# backend/serialio/serial_interface.py

import serial
import time
from backend.serialio.fake_serial import FakeSerial

class SerialInterface:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600, use_fake=False, debug=False):
        self.debug = debug
        if use_fake:
            self.ser = FakeSerial(name=port, debug=debug)
        else:
            self.ser = serial.Serial(port, baudrate, timeout=1)

    # ----------------------- 명령 전송 -----------------------

    # 구조화된 명령어 전송
    def send_command(self, target: str, action: str):
        command = self.build_command(target, action)
        print(f"[Serial Send] {command.strip()}")
        self.ser.write(command.encode())

    # 단순 텍스트 명령 전송
    def write(self, msg: str):
        try:
            self.ser.write((msg + '\n').encode())
        except Exception as e:
            print(f"[SerialInterface 오류] write 실패: {e}")

    # ----------------------- 프로토콜 파싱 -----------------------

    # 명령어 형식 생성
    @staticmethod
    def build_command(target: str, action: str) -> str:
        return f"{target.upper()}_{action.upper()}\n"
    
    # 응답 메시지 파싱
    @staticmethod
    def parse_response(response: str) -> dict:
        if not response:
            return {"type": "EMPTY", "raw": ""}
            
        response = response.strip()
        
        # 디버그 로그 추가 - 모든 응답 표시
        print(f"[🔄 SerialInterface 원본 응답] '{response}'")
        
        # 표준 응답 형식 처리 - ACK:COMMAND:RESULT
        if response.startswith("ACK:"):
            parts = response.split(":")
            if len(parts) >= 2:
                command = parts[1]
                # 결과가 없는 경우 빈 문자열로 처리
                result = parts[2] if len(parts) > 2 else ""
                
                # 디스펜서 특수 명령 처리
                if "DI_" in command:
                    state = None
                    position = None
                    
                    # 상태 감지
                    if "DI_OPENED" in command:
                        state = "OPENED"
                    elif "DI_CLOSED" in command:
                        state = "CLOSED"
                    
                    # 위치 감지
                    if "DI_LOC_A" in command:
                        position = "ROUTE_A"
                    elif "DI_LOC_B" in command:
                        position = "ROUTE_B"
                        
                    # 디스펜서 명령 응답이면 특별히 처리 (DISPENSER 타입으로 변환)
                    if state or position:
                        print(f"[디스펜서 응답 변환] ACK 응답을 DISPENSER 타입으로 변환: {response}")
                        result = {
                            "type": "DISPENSER",
                            "dispenser_id": "DISPENSER",
                            "raw": response
                        }
                        if state:
                            result["state"] = state
                        if position:
                            result["position"] = position
                        return result
                
                # 게이트 특수 명령 처리
                if "GATE_" in command:
                    # ACK:GATE_A_OPENED 또는 ACK:GATE_A_CLOSED 형식 감지
                    gate_id = None
                    state = None
                    
                    # 게이트 ID 추출 (GATE_A, GATE_B, GATE_C)
                    for gate_id_candidate in ["GATE_A", "GATE_B", "GATE_C"]:
                        if gate_id_candidate in command:
                            gate_id = gate_id_candidate
                            break
                    
                    # 상태 감지
                    if "_OPENED" in command:
                        state = "OPENED"
                    elif "_CLOSED" in command:
                        state = "CLOSED"
                        
                    # 게이트 명령 응답이면 특별히 처리 (GATE 타입으로 변환)
                    if gate_id and state:
                        print(f"[게이트 응답 변환] ACK 응답을 GATE 타입으로 변환: {response} -> {gate_id}:{state}")
                        return {
                            "type": "GATE",
                            "gate_id": gate_id,
                            "state": state,
                            "raw": response
                        }
                
                # 일반 ACK 응답 처리
                return {
                    "type": "ACK",
                    "command": command,
                    "result": result,
                    "raw": response
                }
                
        # 상태 응답 처리 - STATUS:TARGET:STATE
        elif response.startswith("STATUS:"):
            parts = response.split(":")
            if len(parts) >= 3:
                target = parts[1]
                state = parts[2]
                
                # 디스펜서 상태 메시지 처리 - 특별히 LOADED인 경우 로그 강화
                if target == "DISPENSER":
                    result = {
                        "type": "DISPENSER",
                        "dispenser_id": "DISPENSER",
                        "state": state,
                        "raw": response
                    }
                    
                    # 위치 정보 추출 (AT_ROUTE_A, AT_ROUTE_B)
                    if state == "AT_ROUTE_A":
                        result["state"] = "READY"  # 상태는 READY로 설정
                        result["position"] = "ROUTE_A"  # 위치 정보 추가
                        print(f"[🔄 디스펜서 위치 인식] 위치: ROUTE_A, 원본: {response}")
                    elif state == "AT_ROUTE_B":
                        result["state"] = "READY"  # 상태는 READY로 설정
                        result["position"] = "ROUTE_B"  # 위치 정보 추가
                        print(f"[🔄 디스펜서 위치 인식] 위치: ROUTE_B, 원본: {response}")
                    # LOADED 상태인 경우 특별 로그
                    elif state == "LOADED" or "LOADED" in state:
                        print(f"[⭐⭐⭐ LOADED 상태 파싱] 타입: DISPENSER, 상태: {state}, 원본: {response}")
                    
                    return result
                    
                # 일반 상태 메시지 처리
                return {
                    "type": "STATUS",
                    "target": target,
                    "state": state,
                    "raw": response
                }
                
        # 게이트 응답 처리 (하위 호환성)
        elif "GATE_" in response:
            if "_OPENED" in response:
                gate_id = None
                for gate_id_candidate in ["GATE_A", "GATE_B", "GATE_C"]:
                    if gate_id_candidate in response:
                        gate_id = gate_id_candidate
                        break
                        
                if not gate_id and response.startswith("GATE_"):
                    parts = response.split("_")
                    if len(parts) >= 2:
                        gate_id = f"{parts[0]}_{parts[1]}"
                
                return {
                    "type": "GATE",
                    "gate_id": gate_id,
                    "state": "OPENED",
                    "raw": response
                }
            elif "_CLOSED" in response:
                gate_id = None
                for gate_id_candidate in ["GATE_A", "GATE_B", "GATE_C"]:
                    if gate_id_candidate in response:
                        gate_id = gate_id_candidate
                        break
                        
                if not gate_id and response.startswith("GATE_"):
                    parts = response.split("_")
                    if len(parts) >= 2:
                        gate_id = f"{parts[0]}_{parts[1]}"
                
                return {
                    "type": "GATE",
                    "gate_id": gate_id,
                    "state": "CLOSED",
                    "raw": response
                }
                
        # 벨트 응답 처리 (하위 호환성)
        elif "BELT" in response:
            if "STARTED" in response or "RUNNING" in response:
                return {
                    "type": "BELT",
                    "state": "RUNNING",
                    "raw": response
                }
            elif "STOPPED" in response:
                return {
                    "type": "BELT",
                    "state": "STOPPED",
                    "raw": response
                }
            elif "EMERGENCY_STOP" in response:
                return {
                    "type": "BELT",
                    "state": "EMERGENCY_STOP",
                    "raw": response
                }
                
        # 이모지 응답 처리
        elif "🔓" in response or "🔒" in response:
            gate_letter = None
            for char in response:
                if char in "ABC":
                    gate_letter = char
                    break
                    
            if gate_letter:
                state = "OPENED" if "🔓" in response else "CLOSED"
                return {
                    "type": "GATE",
                    "gate_id": f"GATE_{gate_letter}",
                    "state": state
                }
                
        # 한글 응답 처리
        elif "게이트" in response:
            gate_letter = None
            for char in response:
                if char in "ABC":
                    gate_letter = char
                    break
                    
            if gate_letter:
                state = "OPENED" if "열림" in response else "CLOSED"
                return {
                    "type": "GATE",
                    "gate_id": f"GATE_{gate_letter}",
                    "state": state
                }
                
        # 컨테이너 상태 처리
        elif response == "ConA_FULL":
            return {
                "type": "CONTAINER",
                "state": "FULL"
            }
            
        # LOADED 문자열이 포함된 응답은 디스펜서 적재 상태로 특별 처리
        elif "LOADED" in response:
            print(f"[⭐⭐⭐ 일반 LOADED 응답 감지] '{response}'")
            return {
                "type": "DISPENSER",
                "dispenser_id": "DISPENSER",
                "state": "LOADED",
                "raw": response
            }
            
        # 알 수 없는 응답
        return {
            "type": "UNKNOWN",
            "raw": response
        }

    # ----------------------- 응답 수신 -----------------------

    # 응답 수신
    def read_response(self, timeout=5):
        start_time = time.time()
        wait_count = 0
        
        print(f"[SerialInterface] 응답 대기 시작 (최대 {timeout}초)")
        
        while time.time() - start_time < timeout:
            # 주기적으로 대기 중임을 표시
            if wait_count % 20 == 0:  # 2초마다 로그
                print(f"[SerialInterface] 응답 대기 중... (경과: {time.time() - start_time:.1f}초)")
            wait_count += 1
            
            if self.ser.in_waiting:
                try:
                    # 반복문으로 여러 줄이 왔을 때 처리 가능하도록
                    line = self.ser.readline().decode().strip()
                    if not line:
                        time.sleep(0.1)
                        continue
                    
                    # 추가 응답이 있는지 확인하고 긴급 처리 (LOADED 메시지)
                    if hasattr(self.ser, 'buffer'):
                        buffer_copy = list(self.ser.buffer)  # 버퍼 복사
                        for item in buffer_copy:
                            buffered_line = item.decode().strip()
                            if "LOADED" in buffered_line:
                                print(f"[🔥 중요 메시지 선제적 처리] '{buffered_line}' 발견")
                    
                    # 응답 파싱
                    parsed = self.parse_response(line)
                    
                    # 응답 타입에 따른 로깅
                    if parsed["type"] == "ACK":
                        command = parsed.get("command", "")
                        result = parsed.get("result", "")
                        print(f"[✅ 명령 응답] {command}: {result}")
                    elif parsed["type"] == "STATUS":
                        target = parsed.get("target", "")
                        state = parsed.get("state", "")
                        print(f"[📊 상태 알림] {target}: {state}")
                    elif parsed["type"] == "GATE":
                        gate_id = parsed.get("gate_id", "")
                        state = parsed.get("state", "")
                        print(f"[🚪 게이트 {gate_id} 상태] {state}")
                    elif parsed["type"] == "BELT":
                        print(f"[🔄 벨트 상태] {parsed['state']}")
                    elif parsed["type"] == "DISPENSER":
                        state = parsed.get("state", "")
                        position = parsed.get("position", "")
                        if state and position:
                            print(f"[🔄 디스펜서 상태] {state}, 위치: {position}")
                        elif state:
                            print(f"[🔄 디스펜서 상태] {state}")
                        elif position:
                            print(f"[🔄 디스펜서 위치] {position}")
                        else:
                            print(f"[🔄 디스펜서 응답] {parsed.get('raw', '')}")
                    elif parsed["type"] == "CONTAINER":
                        print(f"[📦 컨테이너 상태] {parsed['state']}")
                    else:
                        print(f"[ℹ️ 기타 응답] {line}")
                        
                    return line
                    
                except Exception as e:
                    print(f"[SerialInterface 오류] 응답 읽기 실패: {e}")
                    time.sleep(0.1)
                    continue
                    
            time.sleep(0.1)
            
        print(f"[SerialInterface ⚠️] 응답 시간 초과 ({timeout}초)")
        return None

    # 응답 확인만 하고 삭제하지 않음
    def peek_response(self, timeout=0.1):
        """응답 데이터가 있는지 확인하고 있으면 읽어오되, 큐에서 제거하지 않음"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.ser.in_waiting:
                try:
                    line = self.ser.readline().decode().strip()
                    if line:
                        # 큐에서 제거하지 않고 응답만 반환
                        print(f"[🔍 SerialInterface 응답 확인] '{line}'")
                        
                        # 백업 용도로 fake_serial의 경우 큐에 다시 추가
                        if hasattr(self.ser, 'buffer'):
                            # fake_serial인 경우에만 버퍼 조작
                            with self.ser.lock:
                                self.ser.buffer.insert(0, (line + "\n").encode())
                                self.ser.in_waiting = len(self.ser.buffer)
                                
                        return line
                except Exception as e:
                    print(f"[SerialInterface 오류] peek_response 실패: {e}")
                    
            time.sleep(0.01)
            
        return None

    # 시리얼 연결 종료
    def close(self):
        if self.ser:
            self.ser.close()
            print(f"[SerialInterface] 연결 종료") 