# backend/serialio/fake_serial.py

import threading
import time
import re

class FakeSerial:
    # 클래스 레벨 변수로 마지막으로 사용된 게이트 ID 추적
    last_gate_id = "GATE_A"
    
    def __init__(self, name="TRUCK_01", poll_interval=0.1, debug=False):
        self.name = name
        self.buffer = []
        self.in_waiting = 0
        self.lock = threading.Lock()
        self.poll_interval = poll_interval
        self.running = True
        self.debug = debug
        self.polling_thread = threading.Thread(target=self._polling_loop)
        self.polling_thread.daemon = True  # 메인 스레드 종료 시 자동 종료
        self.polling_thread.start()
        
        # 디스펜서 상태 추가
        self.dispenser_state = "CLOSED"  # 초기 상태: 닫힘
        self.dispenser_position = "ROUTE_A"  # 초기 위치: A 경로
        
        if self.debug:
            print(f"[FakeSerial] {name} 인스턴스 생성됨")

    def _polling_loop(self):
        while self.running:
            self.readline()  # 주기적으로 readline 호출
            time.sleep(self.poll_interval)

    def write(self, data: bytes):
        msg = data.decode().strip()
        if self.debug:
            print(f"[FakeSerial:{self.name}] 받은 명령: {msg}")
        
        # 게이트 ID 업데이트 (명령에서 게이트 ID 추출)
        gate_pattern = re.compile(r'(GATE_[ABC])_(\w+)', re.IGNORECASE)
        gate_match = gate_pattern.match(msg)
        if gate_match:
            FakeSerial.last_gate_id = gate_match.group(1).upper()
            if self.debug:
                print(f"[FakeSerial:{self.name}] 마지막 게이트 ID 업데이트: {FakeSerial.last_gate_id}")

        response = self._simulate_response(msg)
        if response:
            with self.lock:
                self.buffer.append((response + "\n").encode())
                self.in_waiting = len(self.buffer)
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 즉시 응답 추가: {response}")

    def readline(self):
        with self.lock:
            if self.buffer:
                response = self.buffer.pop(0)
                self.in_waiting = len(self.buffer)
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 응답 읽기: {response.decode().strip()}")
                return response
            else:
                # 버퍼가 비어있음을 로그로 기록 - 디버그 출력 제거
                # if self.debug:
                #     print(f"[FakeSerial:{self.name}] 버퍼가 비어있음 - 빈 응답 반환")
                return b""

    def _simulate_response(self, msg: str):
        # ✅ 디스펜서 명령 시뮬레이션
        dispenser_pattern = re.compile(r'DISPENSER_(DI_\w+)', re.IGNORECASE)
        dispenser_match = dispenser_pattern.match(msg)
        
        if dispenser_match or "DI_" in msg:
            # 'DISPENSER_' 프리픽스가 없더라도 'DI_' 포함 명령은 디스펜서 명령으로 처리
            command = dispenser_match.group(1) if dispenser_match else msg
            
            if self.debug:
                print(f"[FakeSerial:{self.name}] 디스펜서 명령 감지: {command}")
            
            # 디스펜서 열기
            if "DI_OPEN" in command:
                self.dispenser_state = "OPENED"
                print(f"[FakeSerial:{self.name}] 디스펜서 열림 작업 시작")
                
                # 디스펜서 열린 후 LOADED 상태 보고 - 방식 변경: 즉시 큐에 추가
                print(f"[FakeSerial:{self.name}] 디스펜서 열림 -> LOADED 상태 즉시 큐에 추가 (지연 응답 대신)")
                
                # 즉시 응답 큐에 메시지 추가 - 지연된 응답 대신
                with self.lock:
                    self.buffer.append("ACK:DI_OPENED:OK\n".encode())
                    # LOADED 상태도 바로 큐에 추가 - 안정성을 위해 여러 번 추가
                    self.buffer.append("STATUS:DISPENSER:LOADED\n".encode())
                    self.buffer.append("STATUS:DISPENSER:LOADED\n".encode())
                    self.buffer.append("STATUS:DISPENSER:LOADED\n".encode())
                    self.buffer.append("STATUS:DISPENSER:LOADED\n".encode())
                    self.in_waiting = len(self.buffer)
                    print(f"[FakeSerial:{self.name}] 응답 큐에 LOADED 상태 즉시 추가됨 (큐 크기: {len(self.buffer)})")
                
                # 1초 후에도 LOADED 상태 메시지 추가 (중복 전송으로 안정성 보장)
                def add_delayed_loaded():
                    import time  # 지역 범위에서 time 모듈 임포트
                    time.sleep(1.0)
                    with self.lock:
                        if self.running:  # 실행 중인지 확인
                            self.buffer.append("STATUS:DISPENSER:LOADED\n".encode())
                            self.in_waiting = len(self.buffer)
                            print(f"[FakeSerial:{self.name}] 1초 후 LOADED 상태 추가 완료 (큐 크기: {len(self.buffer)})")
                            
                            # 1.1초 후에 외부 컨트롤러에게 직접 알림
                            time.sleep(0.1)
                            try:
                                # main_controller 직접 임포트 대신 모듈에서 MainController 사용
                                from backend.main_controller.main_controller import MainController
                                import sys
                                
                                # sys.modules에서 main_controller 인스턴스 찾기
                                main_controller = None
                                for module in sys.modules.values():
                                    if hasattr(module, 'main_controller') and isinstance(getattr(module, 'main_controller'), MainController):
                                        main_controller = getattr(module, 'main_controller')
                                        break
                                
                                if main_controller and main_controller.dispenser_controller:
                                    print(f"[FakeSerial:{self.name}] DispenserController에 직접 LOADED 메시지 처리 요청")
                                    main_controller.dispenser_controller.handle_message("STATUS:DISPENSER:LOADED")
                                else:
                                    print(f"[FakeSerial:{self.name}] main_controller 인스턴스를 찾지 못했거나 dispenser_controller가 없습니다.")
                            except Exception as e:
                                print(f"[FakeSerial:{self.name}] DispenserController 직접 호출 오류: {e}")
                                import traceback
                                traceback.print_exc()
                
                # 2초 후에도 LOADED 상태 메시지 추가 (최종 안전장치)
                def add_final_loaded():
                    import time  # 지역 범위에서 time 모듈 임포트
                    time.sleep(2.0)
                    with self.lock:
                        if self.running:  # 실행 중인지 확인
                            self.buffer.append("STATUS:DISPENSER:LOADED\n".encode())
                            self.in_waiting = len(self.buffer)
                            print(f"[FakeSerial:{self.name}] 2초 후 최종 LOADED 상태 추가 완료 (큐 크기: {len(self.buffer)})")
                            
                            # 2.1초 후에 FSM에 직접 DISPENSER_LOADED 이벤트 전달 (최후의 수단)
                            time.sleep(0.1)
                            try:
                                # main_controller 직접 임포트 대신 모듈에서 MainController 사용
                                from backend.main_controller.main_controller import MainController
                                import sys
                                
                                # sys.modules에서 main_controller 인스턴스 찾기
                                main_controller = None
                                for module in sys.modules.values():
                                    if hasattr(module, 'main_controller') and isinstance(getattr(module, 'main_controller'), MainController):
                                        main_controller = getattr(module, 'main_controller')
                                        break
                                
                                if main_controller and main_controller.truck_fsm_manager:
                                    truck_id = "TRUCK_01"  # 기본값
                                    if main_controller.dispenser_controller:
                                        truck_id = main_controller.dispenser_controller.current_truck_id or truck_id
                                    
                                    position = "ROUTE_A"  # 기본값
                                    if main_controller.dispenser_controller:
                                        position = main_controller.dispenser_controller.dispenser_position.get("DISPENSER", position)
                                    
                                    print(f"[FakeSerial:{self.name}] FSM에 직접 DISPENSER_LOADED 이벤트 전달 (트럭: {truck_id}, 위치: {position})")
                                    main_controller.truck_fsm_manager.handle_trigger(truck_id, "DISPENSER_LOADED", {
                                        "dispenser_id": "DISPENSER",
                                        "position": position
                                    })
                                else:
                                    print(f"[FakeSerial:{self.name}] main_controller 인스턴스를 찾지 못했거나 truck_fsm_manager가 없습니다.")
                            except Exception as e:
                                print(f"[FakeSerial:{self.name}] FSM 직접 호출 오류: {e}")
                                import traceback
                                traceback.print_exc()
                
                # 백그라운드에서 지연된 LOADED 메시지 추가
                threading.Thread(target=add_delayed_loaded, daemon=True).start()
                threading.Thread(target=add_final_loaded, daemon=True).start()
                
                # 기존의 지연된 응답은 제거하고 즉시 응답 사용
                return None  # 즉시 응답을 위해 None 반환 (이미 큐에 추가했으므로)
            
            # 디스펜서 닫기
            elif "DI_CLOSE" in command:
                self.dispenser_state = "CLOSED"
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 디스펜서 닫힘 작업 시작")
                return "ACK:DI_CLOSED:OK"
                
            # 왼쪽 회전
            elif "DI_LEFT_TURN" in command:
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 디스펜서 왼쪽 회전")
                return "ACK:DI_LEFT_TURN:OK"
                
            # 오른쪽 회전
            elif "DI_RIGHT_TURN" in command:
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 디스펜서 오른쪽 회전")
                return "ACK:DI_RIGHT_TURN:OK"
                
            # 회전 정지
            elif "DI_STOP_TURN" in command:
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 디스펜서 회전 정지")
                return "ACK:DI_STOP_TURN:OK"
                
            # A 경로 위치 이동
            elif "DI_LOC_ROUTE_A" in command:
                self.dispenser_position = "ROUTE_A"
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 디스펜서 A 경로로 이동")
                
                # 적재 완료 메시지 예약 (A 경로로 이동 3초 후)
                print(f"[FakeSerial:{self.name}] 디스펜서 A 경로 이동 -> LOADED 상태 전송 예약 없음 (OPEN 시 전송)")
                # self._schedule_delayed_response(3.0, "STATUS:DISPENSER:LOADED")
                
                return "ACK:DI_LOC_A:OK"
                
            # B 경로 위치 이동
            elif "DI_LOC_ROUTE_B" in command:
                self.dispenser_position = "ROUTE_B"
                if self.debug:
                    print(f"[FakeSerial:{self.name}] 디스펜서 B 경로로 이동")
                
                # 적재 완료 메시지 예약 (B 경로로 이동 3초 후)
                print(f"[FakeSerial:{self.name}] 디스펜서 B 경로 이동 -> LOADED 상태 전송 예약 없음 (OPEN 시 전송)")
                # self._schedule_delayed_response(3.0, "STATUS:DISPENSER:LOADED")
                
                return "ACK:DI_LOC_B:OK"
        
        # ✅ 게이트 명령 시뮬레이션 - 정규식으로 더 유연하게 처리
        gate_pattern = re.compile(r'(GATE_[ABC])_(\w+)', re.IGNORECASE)
        gate_match = gate_pattern.match(msg)
        
        if gate_match:
            gate_id = gate_match.group(1).upper()
            action = gate_match.group(2).upper()
            
            if self.debug:
                print(f"[FakeSerial:{self.name}] 게이트 명령 감지: {gate_id}_{action}")
            
            if action == "OPEN":
                # 게이트 열림 지연 (0.5초로 단축)
                if self.debug:
                    print(f"[FakeSerial:{self.name}] {gate_id} 열림 작업 시작 (0.5초 소요)")
                
                # 응답 형식 변경: 항상 성공 응답을 보내도록 수정
                # 게이트가 이미 열려있는 것처럼 시뮬레이션
                self._schedule_delayed_response(0.5, f"ACK:{gate_id}_OPENED")
                
                # 상태 메시지도 전송
                self._schedule_delayed_response(0.6, f"STATUS:{gate_id}:OPENED")
                return None  # 즉시 응답 없음, 지연 후 응답이 전송됨
                
            elif action == "CLOSE":
                # 게이트 닫힘 지연 (0.5초로 단축)
                if self.debug:
                    print(f"[FakeSerial:{self.name}] {gate_id} 닫힘 작업 시작 (0.5초 소요)")
                
                # 응답 형식 변경: 항상 성공 응답을 보내도록 수정
                # 게이트가 이미 닫혀있는 것처럼 시뮬레이션
                self._schedule_delayed_response(0.5, f"ACK:{gate_id}_CLOSED")
                
                # 상태 메시지도 전송
                self._schedule_delayed_response(0.6, f"STATUS:{gate_id}:CLOSED")
                return None  # 즉시 응답 없음, 지연 후 응답이 전송됨
        
        # 직접 "OPEN" 명령도 처리
        elif msg == "OPEN":
            # 현재 제어 중인 게이트 ID 결정 (포트 이름에서 추출)
            gate_id = self._extract_gate_id_from_name()
            
            if self.debug:
                print(f"[FakeSerial:{self.name}] 직접 OPEN 명령 감지 - 게이트 ID: {gate_id}")
            
            # 표준 프로토콜 형식 사용
            # ACK:COMMAND:RESULT 형식
            self._schedule_delayed_response(0.5, f"ACK:{gate_id}_OPEN:SUCCESS")
            # 상태 메시지도 전송
            self._schedule_delayed_response(0.6, f"STATUS:{gate_id}:OPENED")
            return None  # 즉시 응답 없음, 지연 후 응답이 전송됨
            
        # 직접 "CLOSE" 명령도 처리
        elif msg == "CLOSE":
            # 현재 제어 중인 게이트 ID 결정 (포트 이름에서 추출)
            gate_id = self._extract_gate_id_from_name()
            
            if self.debug:
                print(f"[FakeSerial:{self.name}] 직접 CLOSE 명령 감지 - 게이트 ID: {gate_id}")
            
            # 표준 프로토콜 형식 사용
            # ACK:COMMAND:RESULT 형식
            self._schedule_delayed_response(0.5, f"ACK:{gate_id}_CLOSE:SUCCESS")
            # 상태 메시지도 전송
            self._schedule_delayed_response(0.6, f"STATUS:{gate_id}:CLOSED")
            return None  # 즉시 응답 없음, 지연 후 응답이 전송됨

        # ✅ 벨트 명령 시뮬레이션
        elif msg == "BELT_RUN":
            if self.debug:
                print(f"[FakeSerial:{self.name}] 벨트 작동 명령 감지")
            # 표준 프로토콜 형식 사용
            # ACK:COMMAND:RESULT 형식
            immediate_response = "ACK:BELT_RUN:SUCCESS"
            # 상태 메시지도 스케줄링
            self._schedule_delayed_response(0.1, "STATUS:BELT:RUNNING")
            self._schedule_delayed_response(20, "STATUS:BELT:STOPPED")
            return immediate_response
            
        elif msg == "BELT_STOP" or msg == "BELTOFF":
            if self.debug:
                print(f"[FakeSerial:{self.name}] 벨트 정지 명령 감지")
            # 표준 프로토콜 형식 사용
            # ACK:COMMAND:RESULT 형식
            return "ACK:BELT_STOP:SUCCESS"
            
        elif msg == "BELT_EMRSTOP" or msg == "EMRSTOP":
            if self.debug:
                print(f"[FakeSerial:{self.name}] 벨트 비상정지 명령 감지")
            # 표준 프로토콜 형식 사용
            # ACK:COMMAND:RESULT 형식
            return "ACK:BELT_EMRSTOP:SUCCESS"
            
        else:
            if self.debug:
                print(f"[FakeSerial:{self.name}] 알 수 없는 명령: {msg}")

        return None
    
    def _extract_gate_id_from_name(self):
        """
        포트 이름/장치 이름에서 게이트 ID를 추출합니다.
        """
        # 포트 이름에 "GATE_"가 있는 경우
        if "GATE_" in self.name:
            return self.name
            
        # 포트 이름에 "DISPENSER"가 있는 경우
        if "DISPENSER" in self.name:
            return "DISPENSER"
        
        # 마지막으로 사용된 게이트 ID 사용
        if FakeSerial.last_gate_id:
            return FakeSerial.last_gate_id
            
        # 포트 이름에 "GATE_"가 없지만 특별한 패턴이 있는 경우
        # 예: /dev/ttyACM1 -> GATE_A, GATE_B 중 하나로 결정
        match = re.search(r'ttyACM(\d+)', self.name)
        if match:
            port_num = int(match.group(1))
            if port_num == 1:  # 예: 여러 게이트가 포트를 공유하는 경우
                return "GATE_A"  # 기본값으로 GATE_A 반환
            elif port_num == 2:
                return "GATE_B"
            elif port_num == 3:
                return "BELT"
            elif port_num == 4:
                return "DISPENSER"
            else:
                return "BELT"  # 다른 포트는 벨트로 가정
        
        # 기본적으로 GATE_A 반환
        return "GATE_A"

    def _schedule_delayed_response(self, delay_seconds, response):
        """
        지연된 응답 전송을 스케줄링합니다.
        
        Args:
            delay_seconds: 지연 시간(초)
            response: 응답 문자열
        """
        if self.debug:
            print(f"[FakeSerial:{self.name}] {delay_seconds}초 후 응답 예약: {response}")
        
        # 스레드 시작 전 running 상태 확인
        if self.running:
            thread = threading.Timer(delay_seconds, self._enqueue_response, args=[response])
            thread.daemon = True  # 메인 스레드 종료 시 자동 종료
            thread.start()

    def _enqueue_response(self, response):
        """
        응답 큐에 메시지를 추가합니다.
        
        Args:
            response: 응답 문자열
        """
        # running 상태 확인
        if not self.running:
            return
            
        with self.lock:
            self.buffer.append((response + "\n").encode())
            self.in_waiting = len(self.buffer)
            if self.debug:
                print(f"[FakeSerial:{self.name}] 응답 큐에 추가됨: {response} (큐 크기: {len(self.buffer)})")

    def close(self):
        """시리얼 연결을 종료합니다."""
        self.running = False
        if hasattr(self, 'polling_thread') and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=1.0)  # 최대 1초 대기
        if self.debug:
            print(f"[FakeSerial:{self.name}] 연결 종료")
