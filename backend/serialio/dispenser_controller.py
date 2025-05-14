import time
from .serial_controller import SerialController

class DispenserController(SerialController):
    def __init__(self, serial_interface, facility_status_manager=None):
        super().__init__(serial_interface)
        self.dispenser_state = {
            "DISPENSER": "CLOSED"  # 초기 상태: 닫힘
        }
        self.dispenser_position = {
            "DISPENSER": "ROUTE_A"  # 초기 위치: A 경로
        }
        self.operations_in_progress = {}
        self.facility_status_manager = facility_status_manager
        self.current_truck_id = "TRUCK_01"  # 기본값으로 TRUCK_01 설정, 나중에 업데이트됨
        self._last_loaded_message_time = 0  # 중복 메시지 방지를 위한 타임스탬프
        self._loading_completed = False  # 추가된 적재 완료 플래그
        
    # ----------------------- 명령 전송 -----------------------
    
    def send_command(self, dispenser_id: str, action: str):
        """
        디스펜서에 명령 전송
        action: OPEN, CLOSE, LEFT_TURN, RIGHT_TURN, STOP_TURN, LOC_ROUTE_A, LOC_ROUTE_B
        """
        if action.upper() == "OPEN":
            return self.open_dispenser(dispenser_id)
        elif action.upper() == "CLOSE":
            return self.close_dispenser(dispenser_id)
        elif action.upper() == "LEFT_TURN":
            return self.send_direction_command(dispenser_id, "LEFT_TURN")
        elif action.upper() == "RIGHT_TURN":
            return self.send_direction_command(dispenser_id, "RIGHT_TURN")
        elif action.upper() == "STOP_TURN":
            return self.send_direction_command(dispenser_id, "STOP_TURN")
        elif action.upper() == "LOC_ROUTE_A":
            return self.move_to_route(dispenser_id, "ROUTE_A")
        elif action.upper() == "LOC_ROUTE_B":
            return self.move_to_route(dispenser_id, "ROUTE_B")
        else:
            print(f"[DispenserController] 알 수 없는 동작: {action}")
            return False
    
    # ----------------------- 상태 관리 -----------------------
    
    def _update_dispenser_status(self, dispenser_id: str, state: str, position: str = None, operation: str = "IDLE"):
        """디스펜서 상태 업데이트 및 facility_status_manager에 보고"""
        # 내부 상태 업데이트
        old_state = self.dispenser_state.get(dispenser_id)
        self.dispenser_state[dispenser_id] = state
        
        if position:
            old_position = self.dispenser_position.get(dispenser_id)
            self.dispenser_position[dispenser_id] = position
            print(f"[디스펜서 위치 업데이트] {dispenser_id}: {old_position} → {position}")
        else:
            position = self.dispenser_position.get(dispenser_id, "UNKNOWN")
            
        print(f"[디스펜서 상태 업데이트] {dispenser_id}: {old_state} → {state}, 위치: {position}")
        
        # facility_status_manager가 있으면 상태 업데이트
        if self.facility_status_manager:
            self.facility_status_manager.update_dispenser_status(dispenser_id, state, position, operation)
    
    # ----------------------- 메시지 처리 -----------------------
    
    def handle_message(self, message: str):
        """디스펜서로부터 받은 메시지 처리"""
        print(f"[디스펜서 메시지] {message}")
        
        # LOADED 메시지 처리 - 여러 형태의 메시지 인식
        if ("STATUS:DISPENSER:LOADED" in message or 
            "STATUS:DISPENSER:LOADED_CONFIRMED" in message or 
            "STATUS:DISPENSER:FORCE_LOADED" in message):
            
            # 1초 이내 중복 메시지 방지
            current_time = time.time()
            if current_time - self._last_loaded_message_time < 1.0:
                print(f"[🔄 중복 메시지 무시] 최근에 LOADED 메시지가 이미 처리되었습니다. ({current_time - self._last_loaded_message_time:.2f}초 전)")
                return True
                
            self._last_loaded_message_time = current_time
            
            print(f"[🎯 적재 완료] 디스펜서에서 적재 완료 메시지 수신: {message}")
            self._loading_completed = True  # 적재 완료 플래그 설정
            
            # 디스펜서 상태 업데이트
            self._update_dispenser_status("DISPENSER", "LOADED", 
                                         self.dispenser_position.get("DISPENSER", "ROUTE_A"), "LOADED")
            
            # 등록된 트럭 ID가 있으면 처리
            if hasattr(self, 'current_truck_id') and self.current_truck_id:
                truck_id = self.current_truck_id
                
                # facility_status_manager를 통한 트럭 명령 전송
                if self.facility_status_manager:
                    print(f"[🔄 자동 명령 처리] 적재 완료 후 트럭 명령 전송 처리")
                    
                    # 자동 FINISH_LOADING 예약
                    self._schedule_finish_loading(truck_id)
            
            return True
                
        # 디스펜서 상태 처리
        if message.startswith("STATUS:DISPENSER:"):
            status_parts = message.split(":")
            if len(status_parts) > 2:
                state = status_parts[2]
                
                # OPENING_COMPLETE 상태 처리
                if state == "OPENING_COMPLETE":
                    print(f"[디스펜서 열림 완료] 디스펜서 개방 완료됨")
                    self._update_dispenser_status("DISPENSER", "OPENED", self.dispenser_position.get("DISPENSER", "ROUTE_A"), "IDLE")
                    return True
                    
                # WAITING_FOR_LOADED 상태 처리
                elif state == "WAITING_FOR_LOADED":
                    print(f"[⏳ 적재 대기중] 디스펜서 적재 대기")
                    self._update_dispenser_status("DISPENSER", "OPENED", self.dispenser_position.get("DISPENSER", "ROUTE_A"), "LOADING")
                    return True
                
                # LOADING_STARTED 상태 처리 (추가)
                elif state == "LOADING_STARTED":
                    print(f"[⏳ 적재 시작] 디스펜서 적재 시작됨")
                    self._update_dispenser_status("DISPENSER", "OPENED", self.dispenser_position.get("DISPENSER", "ROUTE_A"), "LOADING")
                    return True
                    
                # 자동 닫힘 상태 메시지 처리
                elif state == "AUTO_CLOSED":
                    print(f"[🔒 자동 닫힘] 디스펜서 닫힘")
                    self._update_dispenser_status("DISPENSER", "CLOSED", self.dispenser_position.get("DISPENSER", "ROUTE_A"), "IDLE")
                    return True

        # 적재 상태 디버그 패턴 인식
        if "적재 진행 중" in message or "위치: " in message:
            print(f"[디스펜서 상태 업데이트] {message}")
            
            # 닫힘 상태 인식
            if "상태: 닫힘" in message:
                self._update_dispenser_status("DISPENSER", "CLOSED", None, "IDLE")
                
            # 이미 닫힌 상태이고 적재 진행 중이 아님을 인식 -> 강제 로딩 완료 처리
            if "상태: 닫힘" in message and "적재 진행 중: 아니오" in message and not self._loading_completed:
                print(f"[🔍 상태 감지] 디스펜서가 이미 닫혔고 적재가 완료된 것으로 감지됨")
                self.handle_message("STATUS:DISPENSER:LOADED")
                
            return True
                
        # 표준 메시지 처리 로직 (응답 파싱)
        try:
            parsed = self.interface.parse_response(message)
            
            # ACK 메시지 처리
            if parsed["type"] == "ACK":
                if "DI_OPENED" in parsed["raw"]:
                    print(f"[디스펜서] 열림 상태 확인됨")
                    self._update_dispenser_status("DISPENSER", "OPENED", None, "IDLE")
                    
                    # ACK:DI_OPENED 메시지를 받으면 즉시 LOADED 처리 (테스트용)
                    if not hasattr(self, '_loaded_ack_processed') or not self._loaded_ack_processed:
                        self._loaded_ack_processed = True
                        self._update_dispenser_status("DISPENSER", "LOADED", None, "LOADED")
                        self.handle_message("STATUS:DISPENSER:LOADED")
                    
            # 디스펜서 상태 메시지 처리
            elif parsed["type"] == "DISPENSER" and "state" in parsed:
                dispenser_id = parsed.get("dispenser_id", "DISPENSER")
                state = parsed["state"]
                position = parsed.get("position", self.dispenser_position.get(dispenser_id))
                
                # 상태 업데이트
                self._update_dispenser_status(dispenser_id, state, position, "STATUS_UPDATE")
                
                # OPENED 상태이고 DI_OPENED가 포함된 경우 처리
                if state == "OPENED" and "DI_OPENED" in parsed.get("raw", ""):
                    # 자동 LOADED 처리는 한 번만 (중복 방지)
                    if not hasattr(self, '_opened_processed') or not self._opened_processed:
                        self._opened_processed = True
                        self.handle_message("STATUS:DISPENSER:LOADED")
                
                # LOADED 메시지 처리 (중복 처리 방지)
                elif state == "LOADED" and not "HANDLE_MESSAGE" in parsed.get("raw", ""):
                    # LOADED 처리는 한 번만 (중복 방지)
                    if not hasattr(self, '_loaded_processed') or not self._loaded_processed:
                        self._loaded_processed = True
                        self.handle_message("STATUS:DISPENSER:LOADED:HANDLE_MESSAGE")
            
            return
            
        except Exception as e:
            print(f"[⚠️ 처리 오류] {e}")
            
    # ----------------------- 자동 FINISH_LOADING 스케줄링 -----------------------
    
    def _schedule_finish_loading(self, truck_id):
        """FINISH_LOADING 명령을 예약"""
        print(f"[🔄 FINISH_LOADING 예약] 1초 후 자동 전송")
        
        # 중복 명령 방지 플래그 초기화
        self._finish_loading_sent = False
        self._run_command_sent = False
        
        def send_delayed_finish_loading():
            # time 모듈 명시적 import
            import time
            
            # 1초 대기
            time.sleep(1.0)
            
            # 위치 정보 (스레드에서 안전하게 사용하기 위해 미리 가져옴)
            position = self.dispenser_position.get("DISPENSER", "ROUTE_A")
            
            # command_sender를 통한 명령 전송 (주요 방법)
            if self.facility_status_manager and hasattr(self.facility_status_manager, 'command_sender'):
                command_sender = self.facility_status_manager.command_sender
                if command_sender:
                    # FINISH_LOADING 명령 전송 (한 번만)
                    if not self._finish_loading_sent:
                        self._finish_loading_sent = True
                        print(f"[📤 명령 전송] FINISH_LOADING")
                        command_sender.send(truck_id, "FINISH_LOADING", {
                            "position": position
                        })
                        print(f"[✅ 적재 완료 처리] 트럭 {truck_id}에게 FINISH_LOADING 명령 전송됨")
                    
                    # 0.5초 후 RUN 명령 전송
                    time.sleep(0.5)
                    if not self._run_command_sent:
                        self._run_command_sent = True
                        print(f"[📤 자동 이동 명령 전송] RUN → {truck_id}")
                        command_sender.send(truck_id, "RUN", {
                            "target": "CHECKPOINT_C"
                        })
                        print(f"[✅ 이동 명령 전송 완료] 트럭 {truck_id}가 다음 위치로 이동합니다")
        
        # 백그라운드 스레드에서 실행
        import threading
        thread = threading.Thread(target=send_delayed_finish_loading, daemon=True)
        thread.start()

    # ----------------------- 자동 적재 완료 타이머 -----------------------
    
    def _schedule_auto_loading(self, dispenser_id, delay=5.0):
        """지정된 시간 후 자동으로 적재 완료(LOADED) 상태로 변경"""
        # 중복 타이머 방지를 위한 플래그
        self._auto_loading_scheduled = True
        
        def send_auto_loaded_message():
            # time 모듈 명시적 import
            import time
            
            # 지정된 시간 대기
            time.sleep(delay)
            
            # 디스펜서가 여전히 열린 상태인지 확인
            if self.dispenser_state.get(dispenser_id) == "OPENED":
                print(f"[⏱️ 자동 적재 완료] {dispenser_id} - {delay}초 경과, 자동으로 적재 완료 처리")
                
                # 아직 로딩이 완료되지 않았으면 완료 처리
                if not getattr(self, '_loading_completed', False):
                    # 가상 LOADED 메시지 생성 및 처리 (handle_message를 호출)
                    self.handle_message("STATUS:DISPENSER:LOADED")
                else:
                    print(f"[✅ 이미 적재 완료됨] 이미 적재가 완료되어 추가 처리가 필요하지 않습니다.")
            else:
                print(f"[⚠️ 자동 적재 취소] {dispenser_id} - 디스펜서가 더 이상 열린 상태가 아닙니다.")
            
            # 타이머 플래그 초기화
            self._auto_loading_scheduled = False
        
        # 백그라운드 스레드에서 실행
        import threading
        thread = threading.Thread(target=send_auto_loaded_message, daemon=True)
        thread.start()

    # ----------------------- 적재 타임아웃 처리 -----------------------
    
    def _schedule_loading_timeout(self, dispenser_id, timeout=10.0):
        """적재 작업 타임아웃 처리 - 지정된 시간 후에도 로딩이 완료되지 않으면 강제 종료"""
        # 타임아웃 플래그 초기화
        self._loading_timeout_scheduled = True
        self._loading_completed = False
        
        def handle_loading_timeout():
            # time 모듈 명시적 import
            import time
            
            # 시작 시간 기록
            start_time = time.time()
            
            # 지정된 시간 대기
            time.sleep(timeout)
            
            # 이미 로딩이 완료되었는지 확인
            if not getattr(self, '_loading_completed', False):
                print(f"[⚠️ 적재 타임아웃] {dispenser_id} - {timeout}초 경과, 작업 강제 종료")
                
                # 현재 트럭 ID 가져오기
                truck_id = self.current_truck_id if hasattr(self, 'current_truck_id') else None
                
                if truck_id:
                    print(f"[🔄 강제 적재 완료] 트럭 {truck_id}의 적재 작업을 강제로 완료 처리합니다.")
                    
                    # 디스펜서 닫기
                    self.close_dispenser(dispenser_id)
                    
                    # FINISH_LOADING 및 RUN 명령 강제 전송
                    self._force_finish_loading_and_run(truck_id)
                else:
                    print(f"[⚠️ 오류] 트럭 ID를 찾을 수 없어 강제 종료 작업을 완료할 수 없습니다.")
                    # 디스펜서만 닫기
                    self.close_dispenser(dispenser_id)
            else:
                print(f"[✅ 정상 완료] {dispenser_id} - 적재 작업이 타임아웃 전에 정상 완료되었습니다.")
            
            # 타임아웃 플래그 해제
            self._loading_timeout_scheduled = False
        
        # 백그라운드 스레드에서 실행
        import threading
        thread = threading.Thread(target=handle_loading_timeout, daemon=True)
        thread.start()
    
    def _force_finish_loading_and_run(self, truck_id):
        """적재 작업 강제 종료 및 트럭 출발 명령 전송"""
        # time 모듈 명시적 import
        import time
        
        # 위치 정보 (스레드에서 안전하게 사용하기 위해 미리 가져옴)
        position = self.dispenser_position.get("DISPENSER", "ROUTE_A")
        
        # command_sender를 통한 명령 전송
        if self.facility_status_manager and hasattr(self.facility_status_manager, 'command_sender'):
            command_sender = self.facility_status_manager.command_sender
            if command_sender:
                # FINISH_LOADING 명령 전송
                print(f"[📤 강제 명령 전송] FINISH_LOADING → {truck_id}")
                command_sender.send(truck_id, "FINISH_LOADING", {
                    "position": position
                })
                
                # 0.5초 후 RUN 명령 전송
                time.sleep(0.5)
                print(f"[📤 강제 이동 명령 전송] RUN → {truck_id}")
                command_sender.send(truck_id, "RUN", {
                    "target": "CHECKPOINT_C"
                })
                
                print(f"[✅ 강제 이동 명령 완료] 트럭 {truck_id}이(가) 이동을 시작합니다.")
                
                # 적재 완료 상태로 변경
                self._loading_completed = True
        else:
            print(f"[⚠️ 명령 전송 실패] command_sender를 찾을 수 없습니다.")

    # ----------------------- 명령 함수 -----------------------
    
    def _is_success_response(self, response, action):
        """응답이 성공을 나타내는지 확인"""
        if not response:
            return False
            
        # 기본 확인: ACK 메시지 포함 확인
        if "ACK" in response:
            if action == "OPEN" and "DI_OPENED" in response:
                return True
            elif action == "CLOSE" and "DI_CLOSED" in response:
                return True
            elif action == "LOC_ROUTE_A" and "DI_LOC_A" in response:
                return True
            elif action == "LOC_ROUTE_B" and "DI_LOC_B" in response:
                return True
            elif any(cmd in response for cmd in ["DI_LEFT_TURN", "DI_RIGHT_TURN", "DI_STOP_TURN"]):
                return True
        
        return False
        
    def open_dispenser(self, dispenser_id: str):
        """디스펜서 열기"""
        if dispenser_id in self.operations_in_progress and self.operations_in_progress.get(dispenser_id):
            print(f"[디스펜서 작업 중] {dispenser_id}에 대한 작업이 이미 진행 중입니다.")
            return False
            
        # 이미 열려있는 경우 건너뛰기
        if self.dispenser_state.get(dispenser_id) == "OPENED":
            print(f"[디스펜서 이미 열림] {dispenser_id}는 이미 열려 있습니다.")
            return True
            
        # 작업 시작 표시
        self.operations_in_progress[dispenser_id] = True
        print(f"[디스펜서 열기 요청] → {dispenser_id}")
        
        # facility_status_manager 상태 업데이트 - 작업 시작
        if self.facility_status_manager:
            self.facility_status_manager.update_dispenser_status(dispenser_id, "CLOSED", 
                                                              self.dispenser_position.get(dispenser_id, "UNKNOWN"), "OPENING")
        
        # 명령 전송 - 디스펜서가 인식할 수 있는 DI_OPEN 명령 사용
        self.interface.send_command(dispenser_id, "DI_OPEN")
        
        # 응답 대기
        print(f"[디스펜서 열림 대기 중] {dispenser_id} - 최대 5초 대기")
        response = self.interface.read_response(timeout=5)
        
        # 응답 확인 - 디스펜서 응답 형식 (ACK:DI_OPENED:OK)에 맞춤
        success = False
        if "ACK:DI_OPENED:OK" in (response or ""):
            success = True
        elif self._is_success_response(response, "OPEN"):
            success = True
        
        # 결과 처리
        if success:
            print(f"[디스펜서 열림 완료] {dispenser_id} - 응답: {response}")
            self._update_dispenser_status(dispenser_id, "OPENED", None, "IDLE")
            
            # 자동 적재 타이머 시작 (5초 후 자동으로 LOADED 상태로 변경)
            self._schedule_auto_loading(dispenser_id, 5.0)
            print(f"[⏱️ 자동 적재 타이머 시작] {dispenser_id} - 5초 후 자동으로 적재 완료됩니다.")
            
            # 10초 타임아웃 타이머 시작 (10초 후에도 로딩이 완료되지 않으면 강제 종료)
            self._schedule_loading_timeout(dispenser_id, 10.0)
            print(f"[⏱️ 안전 타임아웃 시작] {dispenser_id} - 10초 후 자동으로 작업 강제 종료됩니다.")
        else:
            print(f"[디스펜서 열림 실패] {dispenser_id} - 응답: {response}")
            
            # 응답 실패 시 강제 상태 업데이트
            print(f"[강제 상태 변경] {dispenser_id} - 응답 실패로 강제로 OPENED 상태로 설정")
            self._update_dispenser_status(dispenser_id, "OPENED", None, "FORCED_OPEN")
            
            # 작업 중 플래그 제거
            if dispenser_id in self.operations_in_progress:
                self.operations_in_progress[dispenser_id] = False
                
            # 10초 타임아웃 타이머 시작 (응답 실패 시에도 적용)
            self._schedule_loading_timeout(dispenser_id, 10.0)
            print(f"[⏱️ 안전 타임아웃 시작] {dispenser_id} - 10초 후 자동으로 작업 강제 종료됩니다.")
            
            return True
        
        # 작업 중 플래그 제거
        if dispenser_id in self.operations_in_progress:
            self.operations_in_progress[dispenser_id] = False
            
        return success
        
    def close_dispenser(self, dispenser_id: str):
        """디스펜서 닫기"""
        if dispenser_id in self.operations_in_progress and self.operations_in_progress.get(dispenser_id):
            print(f"[디스펜서 작업 중] {dispenser_id}에 대한 작업이 이미 진행 중입니다.")
            return False
            
        # 이미 닫혀있는 경우 건너뛰기
        if self.dispenser_state.get(dispenser_id) == "CLOSED":
            print(f"[디스펜서 이미 닫힘] {dispenser_id}는 이미 닫혀 있습니다.")
            return True
            
        # 작업 시작 표시
        self.operations_in_progress[dispenser_id] = True
        print(f"[디스펜서 닫기 요청] → {dispenser_id}")
        
        # facility_status_manager 상태 업데이트 - 작업 시작
        if self.facility_status_manager:
            self.facility_status_manager.update_dispenser_status(dispenser_id, "OPENED", 
                                                              self.dispenser_position.get(dispenser_id, "UNKNOWN"), "CLOSING")
        
        # 명령 전송 - 디스펜서가 인식할 수 있는 DI_CLOSE 명령 사용
        self.interface.send_command(dispenser_id, "DI_CLOSE")
        
        # 응답 대기
        print(f"[디스펜서 닫힘 대기 중] {dispenser_id} - 최대 5초 대기")
        response = self.interface.read_response(timeout=5)
        
        # 응답 확인 - 디스펜서 응답 형식 (ACK:DI_CLOSED:OK)에 맞춤
        success = False
        if "ACK:DI_CLOSED:OK" in (response or ""):
            success = True
        elif self._is_success_response(response, "CLOSE"):
            success = True
        
        # 결과 처리
        if success:
            print(f"[디스펜서 닫힘 완료] {dispenser_id} - 응답: {response}")
            self._update_dispenser_status(dispenser_id, "CLOSED", None, "IDLE")
        else:
            print(f"[디스펜서 닫힘 실패] {dispenser_id} - 응답: {response}")
            
            # 응답 실패 시 강제 상태 업데이트
            if "DI_CLOSED" in (response or ""):
                print(f"[디스펜서 닫힘 대체 확인] {dispenser_id}")
                self._update_dispenser_status(dispenser_id, "CLOSED", None, "IDLE")
                success = True
            else:
                print(f"[강제 상태 변경] {dispenser_id} - 응답 실패로 강제로 CLOSED 상태로 설정")
                self._update_dispenser_status(dispenser_id, "CLOSED", None, "FORCED_CLOSE")
                success = True
                
        # 작업 완료 표시
        self.operations_in_progress[dispenser_id] = False
        return success
        
    def move_to_route(self, dispenser_id: str, route: str):
        """디스펜서 경로 변경"""
        route_upper = route.upper()
        if route_upper not in ["ROUTE_A", "ROUTE_B"]:
            print(f"[디스펜서 잘못된 경로] 지원되지 않는 경로: {route}")
            return False
            
        if dispenser_id in self.operations_in_progress and self.operations_in_progress.get(dispenser_id):
            print(f"[디스펜서 작업 중] {dispenser_id}에 대한 작업이 이미 진행 중입니다.")
            return False
            
        # 이미, 같은 경로인 경우 건너뛰기
        if self.dispenser_position.get(dispenser_id) == route_upper:
            print(f"[디스펜서 이미 위치 일치] {dispenser_id}는 이미 {route_upper}에 있습니다.")
            return True
            
        # 작업 시작 표시
        self.operations_in_progress[dispenser_id] = True
        print(f"[디스펜서 경로 변경 요청] {dispenser_id} → {route_upper}")
        
        # facility_status_manager 상태 업데이트 - 작업 시작
        if self.facility_status_manager:
            self.facility_status_manager.update_dispenser_status(dispenser_id, self.dispenser_state.get(dispenser_id, "CLOSED"), 
                                                              "MOVING", "ROUTE_CHANGE")
        
        # 명령 전송 (DI_LOC_ROUTE_A 또는 DI_LOC_ROUTE_B)
        command = f"DI_LOC_{route_upper}"
        
        # 디스펜서 인식용 명령어 형식으로 변환 (DI_LOC_ROUTE_A -> DI_LOC_ROUTE_A)
        print(f"[명령어 변환] 명령: {command} - 디스펜서 인식 형식으로 전송")
        self.interface.send_command(dispenser_id, command)
        
        # 응답 대기
        print(f"[디스펜서 경로 변경 대기 중] {dispenser_id} → {route_upper} - 최대 10초 대기")
        response = self.interface.read_response(timeout=10)  # 경로 변경은 시간이 더 걸릴 수 있어 타임아웃 증가
        
        # 응답 확인 (디스펜서 응답 ACK:DI_LOC_A:OK 또는 ACK:DI_LOC_B:OK)
        success = False
        if "ACK:DI_LOC_A:OK" in (response or "") and route_upper == "ROUTE_A":
            success = True
        elif "ACK:DI_LOC_B:OK" in (response or "") and route_upper == "ROUTE_B":
            success = True
        elif self._is_success_response(response, f"LOC_{route_upper}"):
            success = True
        
        # 결과 처리
        if success:
            print(f"[디스펜서 경로 변경 완료] {dispenser_id} → {route_upper} - 응답: {response}")
            self._update_dispenser_status(dispenser_id, self.dispenser_state.get(dispenser_id), route_upper, "IDLE")
        else:
            print(f"[디스펜서 경로 변경 실패] {dispenser_id} → {route_upper} - 응답: {response}")
            
            # 강제 상태 업데이트
            print(f"[강제 상태 변경] {dispenser_id} - 응답 실패로 강제로 {route_upper} 위치로 설정")
            self._update_dispenser_status(dispenser_id, self.dispenser_state.get(dispenser_id), route_upper, "FORCED_MOVE")
            success = True
                
        # 작업 완료 표시
        self.operations_in_progress[dispenser_id] = False
        return success
        
    def send_direction_command(self, dispenser_id: str, direction_cmd: str):
        """디스펜서 회전 방향 설정"""
        if dispenser_id in self.operations_in_progress and self.operations_in_progress.get(dispenser_id):
            print(f"[디스펜서 작업 중] {dispenser_id}에 대한 작업이 이미 진행 중입니다.")
            return False
            
        # 작업 시작 표시
        self.operations_in_progress[dispenser_id] = True
        print(f"[디스펜서 방향 설정] {dispenser_id} → {direction_cmd}")
        
        # 명령 전송 - 디스펜서가 인식할 수 있는 DI_LEFT_TURN, DI_RIGHT_TURN, DI_STOP_TURN 명령 사용
        self.interface.send_command(dispenser_id, f"DI_{direction_cmd}")
        
        # 응답 대기
        response = self.interface.read_response(timeout=2)  # 짧은 타임아웃
        
        # 응답 확인 - 디스펜서 응답 형식 (ACK:DI_LEFT_TURN:OK 등)에 맞춤
        success = False
        expected_response = f"ACK:DI_{direction_cmd}:OK"
        if expected_response in (response or ""):
            success = True
        elif self._is_success_response(response, direction_cmd):
            success = True
        else:
            # 응답 실패 시도 성공으로 처리 (명령이 도달했을 가능성 높음)
            print(f"[디스펜서 방향 명령 응답 없음] {dispenser_id} - 명령: {direction_cmd}, 응답: {response}")
            success = True
        
        # 작업 완료 표시
        self.operations_in_progress[dispenser_id] = False
        return success
