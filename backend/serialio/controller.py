import serial
import time
from .protocol import SerialProtocol

class SerialController:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600):
        self.ser = serial.Serial(port, baudrate, timeout=1)

    def send_command(self, target: str, action: str):
        command = SerialProtocol.build_command(target, action)
        print(f"[Serial Send] {command.strip()}")
        self.ser.write(command.encode())

    def read_response(self, timeout=3):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.ser.in_waiting:
                line = self.ser.readline().decode().strip()
                if line.startswith("ACK:") or line.startswith("STATUS:"):
                    parsed = SerialProtocol.parse_response(line)
                    print(f"[Serial Read] {parsed}")
                    return parsed
                else:
                    print(f"[Serial Debug] {line}")
            time.sleep(0.05)
        print("[Serial Timeout] 응답 없음")
        return None

    
    def close(self):
        self.ser.close()