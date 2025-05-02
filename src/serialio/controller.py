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


# ---------------------------------------------------------------

# 가상 시리얼 장치 테스트용

# from tests.serial.virtual_serial_device import VirtualSerialDevice as Serial

# class SerialController:
#     def __init__(self, serial_instance=None):
#         self.ser = serial_instance or Serial()

#     def send_command(self, target: str, action: str):
#         command = f"{target.upper()}_{action.upper()}\n"
#         print(f"[Serial ▶] {command.strip()}")
#         self.ser.write(command.encode())

#     def read_response(self):
#         if self.ser.in_waiting():
#             line = self.ser.readline().decode().strip()
#             print(f"[Serial ◀] {line}")
#             return line
#         return None

#     def close(self):
#         self.ser.close()

