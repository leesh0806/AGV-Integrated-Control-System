# backend/serialio/port_manager.py

from .belt_controller import BeltController
from .gate_controller import GateController
from typing import Dict, Optional
import serial
import time
import importlib

# FakeSerial 클래스 임포트
try:
    from .fake_serial import FakeSerial
except ImportError:
    # FakeSerial 클래스 정의 (임시)
    class FakeSerial:
        def __init__(self, *args, **kwargs):
            self.buffer = ""
            print("[FakeSerial] 가상 시리얼 초기화")
        
        def write(self, data):
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            print(f"[FakeSerial] 전송: {data}")
            return len(data)
        
        def read_until(self, terminator=b'\n', timeout=None):
            return b"ACK:GATE_A_OPENED\n"
        
        def close(self):
            print("[FakeSerial] 연결 종료")


class SerialController:
    """시리얼 컨트롤러 클래스"""
    def __init__(self, port, use_fake=False):
        self.port = port
        self.use_fake = use_fake
        
        if use_fake:
            self.serial = FakeSerial()
            print(f"[SerialController] 가상 시리얼 모드 사용 ({port})")
        else:
            self.serial = serial.Serial(port, 9600, timeout=1.0)
            print(f"[SerialController] 실제 시리얼 포트 연결 ({port})")
    
    def write(self, data):
        """데이터 쓰기"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.serial.write(data)
    
    def read_response(self, timeout=5):
        """응답 읽기"""
        if self.use_fake:
            # 가상 모드면 지연 후 성공 응답 반환
            time.sleep(1)  # 가상 지연
            if "GATE_A" in self.port:
                return "ACK:GATE_A_OPENED"
            elif "GATE_B" in self.port:
                return "ACK:GATE_B_OPENED"
            elif "BELT" in self.port:
                return "BELTON"
        else:
            # 실제 시리얼 포트에서 읽기 시도
            self.serial.timeout = timeout
            response = self.serial.read_until(b'\n')
            if response:
                return response.decode('utf-8').strip()
        return None
    
    def close(self):
        """연결 종료"""
        self.serial.close()


class PortManager:
    def __init__(self, port_map: dict, use_fake=False):
        self.controllers = {}
        print(f"[PortManager] 시리얼 관리자 초기화 - {'가상' if use_fake else '실제'} 모드")
        print(f"[PortManager] 포트 맵: {port_map}")
        
        for name, port in port_map.items():
            print(f"[PortManager] 컨트롤러 생성: {name} → {port}")
            
            # 각 장치별 시리얼 컨트롤러 생성
            device_controller = SerialController(port, use_fake)
            
            # 장치별 전용 컨트롤러 생성하여 저장
            if "BELT" in name.upper():
                self.controllers[name] = BeltController(device_controller)
            elif "GATE" in name.upper():
                self.controllers[name] = device_controller  # SerialController 저장
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
            controller.write(action)  # 직접 write 호출
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
