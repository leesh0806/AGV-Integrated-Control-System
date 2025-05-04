# backend/serialio/controller.py

import serial
import time
from backend.serialio.protocol import SerialProtocol
from backend.serialio.fake_serial import FakeSerial

class SerialController:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600, use_fake=False):
        if use_fake:
            self.ser = FakeSerial(name=port)  # ✅ 가상 시리얼 사용
        else:
            self.ser = serial.Serial(port, baudrate, timeout=1)

    def send_command(self, target: str, action: str):
        """
        구조화된 명령어 전송: ex) GATE_A + OPEN → 'GATE_A:OPEN'
        """
        command = SerialProtocol.build_command(target, action)
        print(f"[Serial Send] {command.strip()}")
        self.ser.write(command.encode())

    def write(self, msg: str):
        """
        단순 텍스트 명령 전송 (예: BELTACT, BELTOFF 등)
        """
        try:
            self.ser.write((msg + '\n').encode())
        except Exception as e:
            print(f"[SerialController 오류] write 실패: {e}")

    def read_response(self, timeout=3):
        """
        응답 수신 (ACK 또는 장치 상태 등) → 문자열로 반환
        ✅ 벨트의 BELTON/BELTOFF/ConA_FULL 같은 응답도 로깅
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.ser.in_waiting:
                line = self.ser.readline().decode().strip()

                # ✅ FakeSerial 응답일 경우 "STATUS:" 프리픽스를 제거
                if line.startswith("STATUS:"):
                    line = line.replace("STATUS:", "", 1)

                # ✅ 벨트 상태 응답 로깅
                if any(status in line for status in ["BELTON", "BELTOFF", "ConA_FULL"]):
                    print(f"[🔄 벨트 상태] {line}")
                    return line
                elif line.startswith("ACK:"):
                    print(f"[✅ ACK 응답] {line}")
                    return line
                else:
                    print(f"[ℹ️ 기타 응답] {line}")

            time.sleep(0.05)
        print("[⏰ 응답 시간 초과]")
        return None

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass
