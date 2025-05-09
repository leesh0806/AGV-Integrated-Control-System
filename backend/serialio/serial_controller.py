# backend/serialio/serial_controller.py

import serial
import time
from backend.serialio.protocol import SerialProtocol
from backend.serialio.fake_serial import FakeSerial

class SerialController:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600, use_fake=False):
        if use_fake:
            self.ser = FakeSerial(name=port)
        else:
            self.ser = serial.Serial(port, baudrate, timeout=1)

    # ----------------------- 명령 전송 -----------------------

    # 구조화된 명령어 전송
    def send_command(self, target: str, action: str):
        command = SerialProtocol.build_command(target, action)
        print(f"[Serial Send] {command.strip()}")
        self.ser.write(command.encode())

    # 단순 텍스트 명령 전송
    def write(self, msg: str):
        try:
            self.ser.write((msg + '\n').encode())
        except Exception as e:
            print(f"[SerialController 오류] write 실패: {e}")

    # ----------------------- 응답 수신 -----------------------

    # 응답 수신
    def read_response(self, timeout=5):
        start_time = time.time()
        wait_count = 0
        
        print(f"[SerialController] 응답 대기 시작 (최대 {timeout}초)")
        
        while time.time() - start_time < timeout:
            # 주기적으로 대기 중임을 표시
            if wait_count % 20 == 0:  # 2초마다 로그
                print(f"[SerialController] 응답 대기 중... (경과: {time.time() - start_time:.1f}초)")
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

                    # 게이트 응답 처리 개선
                    if "GATE_" in line and "OPENED" in line:
                        print(f"[🚪 게이트 열림 응답] {line}")
                        return line
                    elif "GATE_" in line and "CLOSED" in line:
                        print(f"[🚪 게이트 닫힘 응답] {line}")
                        return line
                    
                    # 벨트 상태 응답 로깅
                    elif any(status in line for status in ["BELTON", "BELTOFF", "ConA_FULL"]):
                        print(f"[🔄 벨트 상태] {line}")
                        return line
                    elif line.startswith("ACK:"):
                        print(f"[✅ ACK 응답] {line}")
                        return line
                    else:
                        print(f"[ℹ️ 기타 응답] {line}")
                        return line  # 알 수 없는 응답도 반환
                    
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