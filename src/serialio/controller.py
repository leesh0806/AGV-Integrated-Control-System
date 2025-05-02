import serial
from .protocol import SerialProtocol

class SerialController:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600):
        self.ser = serial.Serial(port, baudrate, timeout=1)

    def send_command(self, target: str, action: str):
        command = SerialProtocol.build_command(target, action)
        print(f"[Serial Send] {command.strip()}")
        self.ser.write(command.encode())

    def read_response(self):
        if self.ser.in_waiting:
            line = self.ser.readline().decode().strip()
            parsed = SerialProtocol.parse_response(line)
            print(f"[Serial Read] {parsed}")
            return parsed
        return None
    
    def close(self):
        self.ser.close()