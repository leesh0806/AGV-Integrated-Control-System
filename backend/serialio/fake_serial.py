# backend/serialio/fake_serial.py

import threading
import time
import re

class FakeSerial:
    def __init__(self, name="TRUCK_01"):
        self.name = name
        self.buffer = []
        self.in_waiting = 0
        self.lock = threading.Lock()
        print(f"[FakeSerial] {name} 인스턴스 생성됨")

    def write(self, data: bytes):
        msg = data.decode().strip()
        print(f"[FakeSerial:{self.name}] 받은 명령: {msg}")

        response = self._simulate_response(msg)
        if response:
            with self.lock:
                self.buffer.append((response + "\n").encode())
                self.in_waiting = len(self.buffer)
                print(f"[FakeSerial:{self.name}] 즉시 응답 추가: {response}")

    def readline(self):
        with self.lock:
            if self.buffer:
                response = self.buffer.pop(0)
                self.in_waiting = len(self.buffer)
                print(f"[FakeSerial:{self.name}] 응답 읽기: {response.decode().strip()}")
                return response
            else:
                # 버퍼가 비어있음을 로그로 기록
                print(f"[FakeSerial:{self.name}] 버퍼가 비어있음 - 빈 응답 반환")
                return b""

    def _simulate_response(self, msg: str):
        # ✅ 게이트 명령 시뮬레이션 - 정규식으로 더 유연하게 처리
        gate_pattern = re.compile(r'(GATE_[ABC])_(\w+)', re.IGNORECASE)
        gate_match = gate_pattern.match(msg)
        
        if gate_match:
            gate_id = gate_match.group(1).upper()
            action = gate_match.group(2).upper()
            
            print(f"[FakeSerial:{self.name}] 게이트 명령 감지: {gate_id}_{action}")
            
            if action == "OPEN":
                # 게이트 열림 지연 (0.5초로 단축)
                print(f"[FakeSerial:{self.name}] {gate_id} 열림 작업 시작 (0.5초 소요)")
                self._schedule_delayed_response(0.5, f"ACK:{gate_id}_OPENED")
                return None  # 즉시 응답 없음, 지연 후 응답이 전송됨
            elif action == "CLOSE":
                # 게이트 닫힘 지연 (0.5초로 단축)
                print(f"[FakeSerial:{self.name}] {gate_id} 닫힘 작업 시작 (0.5초 소요)")
                self._schedule_delayed_response(0.5, f"ACK:{gate_id}_CLOSED")
                return None  # 즉시 응답 없음, 지연 후 응답이 전송됨
        
        # 직접 "OPEN" 명령도 처리
        elif msg == "OPEN":
            # 장치 이름이 아닌 현재 제어 중인 게이트 ID(GATE_A, GATE_B 등)를 사용
            # 이 부분이 문제 - 현재 SerialInterface에서는 인스턴스 이름을 응답에 사용함
            # 응답 시 self.name이 게이트 ID가 아닌 경우 문제가 발생할 수 있음
            print(f"[FakeSerial:{self.name}] {self.name} 직접 OPEN 명령 감지")
            
            # 장치 이름에서 게이트 ID를 추출하거나 그대로 사용
            if "GATE_" in self.name:
                gate_id = self.name  # 이미 게이트 ID인 경우
            else:
                # 이름에 따라 게이트 ID를 결정 (FakeSerial 이름을 게이트 ID로 설정한 경우 사용)
                gate_id = self.name
            
            # 응답 메시지 예약
            self._schedule_delayed_response(0.5, f"ACK:{gate_id}_OPENED")
            return None  # 즉시 응답 없음, 지연 후 응답이 전송됨
            
        # 직접 "CLOSE" 명령도 처리
        elif msg == "CLOSE":
            # 응답 시 적절한 게이트 ID 사용
            print(f"[FakeSerial:{self.name}] {self.name} 직접 CLOSE 명령 감지")
            
            # 장치 이름에서 게이트 ID를 추출하거나 그대로 사용
            if "GATE_" in self.name:
                gate_id = self.name  # 이미 게이트 ID인 경우
            else:
                # 이름에 따라 게이트 ID를 결정 (FakeSerial 이름을 게이트 ID로 설정한 경우 사용)
                gate_id = self.name
            
            # 응답 메시지 예약
            self._schedule_delayed_response(0.5, f"ACK:{gate_id}_CLOSED")
            return None  # 즉시 응답 없음, 지연 후 응답이 전송됨

        # ✅ 벨트 명령 시뮬레이션
        elif msg == "BELT_RUN":
            print(f"[FakeSerial:{self.name}] 벨트 작동 명령 감지")
            self._schedule_delayed_response(0.5, "STATUS:BELT:RUNNING")
            self._schedule_delayed_response(20, "STATUS:BELT:STOPPED")
            return "ACK:BELT:STARTED"
        elif msg == "BELTOFF":
            print(f"[FakeSerial:{self.name}] 벨트 정지 명령 감지")
            return "ACK:BELT:STOPPED"
        elif msg == "EMRSTOP":
            print(f"[FakeSerial:{self.name}] 벨트 비상정지 명령 감지")
            return "ACK:BELT:EMERGENCY_STOP"
        else:
            print(f"[FakeSerial:{self.name}] 알 수 없는 명령: {msg}")

        return None

    def _schedule_delayed_response(self, delay_seconds, response):
        """
        지연된 응답 전송을 스케줄링합니다.
        """
        print(f"[FakeSerial:{self.name}] {delay_seconds}초 후 응답 예약: {response}")
        threading.Timer(delay_seconds, self._enqueue_response, args=[response]).start()

    def _enqueue_response(self, response):
        with self.lock:
            self.buffer.append((response + "\n").encode())
            self.in_waiting = len(self.buffer)
            print(f"[FakeSerial:{self.name}] 응답 큐에 추가됨: {response} (큐 크기: {len(self.buffer)})")

    def close(self):
        print(f"[FakeSerial:{self.name}] 연결 종료")
        pass
