# backend/serialio/serial_interface.py

import serial
import time
from backend.serialio.serial_protocol_parser import SerialProtocolParser
from backend.serialio.fake_serial import FakeSerial

class SerialInterface:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600, use_fake=False):
        if use_fake:
            # port 값을 FakeSerial의 name으로 사용
            # port는 보통 장치 ID와 동일한 값으로 설정됩니다 (e.g. "GATE_A", "GATE_B")
            self.ser = FakeSerial(name=port)
        else:
            self.ser = serial.Serial(port, baudrate, timeout=1)

    # ----------------------- 명령 전송 -----------------------

    # 구조화된 명령어 전송
    def send_command(self, target: str, action: str):
        command = SerialProtocolParser.build_command(target, action)
        print(f"[Serial Send] {command.strip()}")
        self.ser.write(command.encode())

    # 단순 텍스트 명령 전송
    def write(self, msg: str):
        try:
            self.ser.write((msg + '\n').encode())
        except Exception as e:
            print(f"[SerialInterface 오류] write 실패: {e}")

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
                    
                    # FakeSerial 응답일 경우 
                    # "STATUS:" 프리픽스를 제거
                    if line.startswith("STATUS:"):
                        line = line.replace("STATUS:", "", 1)

                    # ✨ 아두이노 응답 형식 처리 개선
                    # 게이트 응답 처리 - 기존 형식 (ACK:GATE_X_OPENED/CLOSED)
                    if "GATE_" in line and ("OPENED" in line or "CLOSED" in line):
                        if "OPENED" in line:
                            print(f"[🚪 게이트 열림 응답] {line}")
                        else:
                            print(f"[🚪 게이트 닫힘 응답] {line}")
                        return line
                        
                    # 게이트 응답 처리 - 아두이노 이모지 형식 (🔓 게이트A 열림, 🔒 게이트B 닫힘)
                    elif ("게이트" in line and "열림" in line) or ("게이트" in line and "닫힘" in line) or ("🔓" in line or "🔒" in line):
                        # 게이트 열림 응답
                        if "열림" in line or "🔓" in line:
                            print(f"[🚪 게이트 열림 응답] {line}")
                            # 어떤 게이트인지 추출
                            if "게이트A" in line or "게이트 A" in line:
                                return "ACK:GATE_A_OPENED"
                            elif "게이트B" in line or "게이트 B" in line:
                                return "ACK:GATE_B_OPENED"
                            else:
                                # 게이트 ID를 추출할 수 없는 경우
                                return f"GATE_OPENED:{line}"
                                
                        # 게이트 닫힘 응답
                        elif "닫힘" in line or "🔒" in line:
                            print(f"[🚪 게이트 닫힘 응답] {line}")
                            # 어떤 게이트인지 추출
                            if "게이트A" in line or "게이트 A" in line:
                                return "ACK:GATE_A_CLOSED"
                            elif "게이트B" in line or "게이트 B" in line:
                                return "ACK:GATE_B_CLOSED"
                            else:
                                # 게이트 ID를 추출할 수 없는 경우
                                return f"GATE_CLOSED:{line}"
                    
                    # 벨트 상태 응답 로깅
                    elif any(status in line for status in ["BELTON", "BELTOFF", "ConA_FULL", "벨트", "Belt"]):
                        print(f"[🔄 벨트 상태] {line}")
                        if "작동" in line or "시작" in line or "ON" in line or "BELTON" in line:
                            return "ACK:BELT:STARTED"
                        elif "정지" in line or "멈춤" in line or "OFF" in line or "BELTOFF" in line:
                            return "ACK:BELT:STOPPED"
                        else:
                            return line
                            
                    elif line.startswith("ACK:"):
                        print(f"[✅ ACK 응답] {line}")
                        return line
                    else:
                        print(f"[ℹ️ 기타 응답] {line}")
                        # 현재 처리 중인 명령에 맞게 응답 변환 (컨트롤러에서 활용)
                        return line
                    
                except UnicodeDecodeError:
                    print("[⚠️ 디코딩 오류] 응답을 해석할 수 없습니다.")
                    continue

            # 짧은 대기 시간으로 CPU 사용량 감소
            time.sleep(0.1)
        
        print(f"[⏰ 응답 시간 초과 ({timeout}초)]")
        return None
    

    # ----------------------- 연결 종료 -----------------------

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass 