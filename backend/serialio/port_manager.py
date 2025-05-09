# backend/serialio/port_manager.py

from .belt_controller import BeltController
from .gate_controller import GateController
from typing import Dict, Optional
import serial
import time

class PortManager:
    def __init__(self, port_map: dict, use_fake=False):
        self.controllers = {}
        print(f"[PortManager] 시리얼 관리자 초기화 - {'가상' if use_fake else '실제'} 모드")
        print(f"[PortManager] 포트 맵: {port_map}")
        
        for name, port in port_map.items():
            print(f"[PortManager] 컨트롤러 생성: {name} → {port}")
            if "BELT" in name.upper():
                self.controllers[name] = BeltController(port=port, use_fake=use_fake)
            elif "GATE" in name.upper():
                self.controllers[name] = GateController(port=port, use_fake=use_fake)
            else:
                print(f"[PortManager ⚠️] 알 수 없는 장치 유형: {name}")
        
        print(f"[PortManager] 등록된 컨트롤러: {list(self.controllers.keys())}")

    def send_command(self, facility: str, action: str):
        """
        지정된 시설에 명령을 전송합니다.
        
        Args:
            facility (str): 명령을 보낼 시설/장치 이름 (예: "GATE_A")
            action (str): 전송할 명령 (예: "OPEN")
        """
        print(f"[PortManager] 명령 전송 시도: {facility} → {action}")
        controller = self.controllers.get(facility)
        if controller:
            print(f"[PortManager] {facility}({facility in self.controllers}) → {action} 명령 전송")
            controller.send_command(action)  # action만 전달
        else:
            print(f"[PortManager ❌] {facility} 장치가 등록되지 않았습니다. 등록된 장치: {list(self.controllers.keys())}")

    def read_response(self, facility: str, timeout=5):
        """
        특정 시설의 응답을 읽습니다.
        
        Args:
            facility (str): 응답을 읽을 시설/장치의 이름 (예: "GATE_A")
            timeout (int): 응답 대기 시간(초). 기본값은 5초.
            
        Returns:
            str: 수신된 응답 문자열. 시간 초과 또는 오류 시 None.
        """
        print(f"[PortManager] {facility}에서 응답 읽기 시도 (타임아웃: {timeout}초)")
        controller = self.controllers.get(facility)
        if controller:
            print(f"[PortManager] {facility} 컨트롤러에서 응답 읽기 시작")
            response = controller.read_response(timeout=timeout)
            print(f"[PortManager] {facility} 응답 읽기 완료: {response}")
            return response
        print(f"[PortManager ❌] {facility} 장치가 등록되지 않았습니다. 등록된 장치: {list(self.controllers.keys())}")
        return None

    def close_all(self):
        print(f"[PortManager] 모든 컨트롤러 종료 중...")
        for name, controller in self.controllers.items():
            print(f"[PortManager] {name} 컨트롤러 종료")
            controller.close()
        print(f"[PortManager] 모든 컨트롤러 종료 완료")
