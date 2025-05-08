# backend/serialio/serial_manager.py

from backend.serialio.serial_controller import SerialController

class SerialManager:
    def __init__(self, port_map: dict, use_fake=False):
        self.controllers = {}
        print(f"[SerialManager] 시리얼 관리자 초기화 - {'가상' if use_fake else '실제'} 모드")
        print(f"[SerialManager] 포트 맵: {port_map}")
        
        for name, port in port_map.items():
            print(f"[SerialManager] 컨트롤러 생성: {name} → {port}")
            self.controllers[name] = SerialController(port=port, use_fake=use_fake)
        
        print(f"[SerialManager] 등록된 컨트롤러: {list(self.controllers.keys())}")

    def send_command(self, facility: str, action: str):
        """
        지정된 시설에 명령을 전송합니다.
        
        Args:
            facility (str): 명령을 보낼 시설/장치 이름 (예: "GATE_A")
            action (str): 전송할 명령 (예: "OPEN")
        """
        print(f"[SerialManager] 명령 전송 시도: {facility} → {action}")
        controller = self.controllers.get(facility)
        if controller:
            print(f"[SerialManager] {facility}({facility in self.controllers}) → {action} 명령 전송")
            controller.send_command(facility, action)  # 두 인자 명확히 전달
        else:
            print(f"[SerialManager ❌] {facility} 장치가 등록되지 않았습니다. 등록된 장치: {list(self.controllers.keys())}")

    def read_response(self, facility: str, timeout=5):
        """
        특정 시설의 응답을 읽습니다.
        
        Args:
            facility (str): 응답을 읽을 시설/장치의 이름 (예: "GATE_A")
            timeout (int): 응답 대기 시간(초). 기본값은 5초.
            
        Returns:
            str: 수신된 응답 문자열. 시간 초과 또는 오류 시 None.
        """
        print(f"[SerialManager] {facility}에서 응답 읽기 시도 (타임아웃: {timeout}초)")
        controller = self.controllers.get(facility)
        if controller:
            print(f"[SerialManager] {facility} 컨트롤러에서 응답 읽기 시작")
            response = controller.read_response(timeout=timeout)
            print(f"[SerialManager] {facility} 응답 읽기 완료: {response}")
            return response
        print(f"[SerialManager ❌] {facility} 장치가 등록되지 않았습니다. 등록된 장치: {list(self.controllers.keys())}")
        return None

    def close_all(self):
        print(f"[SerialManager] 모든 컨트롤러 종료 중...")
        for name, controller in self.controllers.items():
            print(f"[SerialManager] {name} 컨트롤러 종료")
            controller.close()
        print(f"[SerialManager] 모든 컨트롤러 종료 완료")
