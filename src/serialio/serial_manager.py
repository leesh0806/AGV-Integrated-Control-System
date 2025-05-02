# serialio/serial_manager.py

from serialio.controller import SerialController

class SerialManager:
    def __init__(self, port_map: dict):
        self.controllers = {
            facility: SerialController(port=port)
            for facility, port in port_map.items()
        }

    def send_command(self, facility: str, action: str):
        if facility in self.controllers:
            print(f"[SerialManager] {facility} → {action}")
            self.controllers[facility].send_command(facility, action)
        else:
            print(f"[SerialManager 오류] {facility} 장치가 등록되지 않았습니다.")

    def read_response(self, facility: str):
        if facility in self.controllers:
            return self.controllers[facility].read_response()
        return None
    
    def close_all(self):
        for controller in self.controllers.values():
            controller.close()