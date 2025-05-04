# backend/serialio/serial_manager.py

from backend.serialio.controller import SerialController

class SerialManager:
    def __init__(self, port_map: dict, use_fake=False):
        self.controllers = {}
        for name, port in port_map.items():
            self.controllers[name] = SerialController(port=port, use_fake=use_fake)

    def send_command(self, facility: str, action: str):
        controller = self.controllers.get(facility)
        if controller:
            print(f"[SerialManager] {facility} → {action}")
            controller.send_command(facility, action)  # 두 인자 명확히 전달
        else:
            print(f"[SerialManager 오류] {facility} 장치가 등록되지 않았습니다.")

    def read_response(self, facility: str):
        controller = self.controllers.get(facility)
        if controller:
            return controller.read_response()
        print(f"[SerialManager 오류] {facility} 장치가 등록되지 않았습니다.")
        return None

    def close_all(self):
        for controller in self.controllers.values():
            controller.close()
