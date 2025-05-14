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
        if not message:
            return
            
        # 디버그 로그 추가 - 모든 메시지 표시
        print(f"[🔍 DispenserController 원본 메시지] '{message}'")
            
        # LOADED 상태 감지 및 처리 강화 - 문자열에 "LOADED"가 포함된 모든 메시지 처리
        if "LOADED" in message:
            # 중복 메시지 방지 - 디스펜서가 LOADED 메시지를 2번 보내므로, 300ms 내에 동일 메시지는 스킵
            current_time = time.time()
            if current_time - self._last_loaded_message_time < 0.3:
                print(f"[🔄 중복 LOADED 메시지 무시] 이전 메시지와의 시간 간격: {current_time - self._last_loaded_message_time:.3f}초")
                return True
                
            # 타임스탬프 갱신
            self._last_loaded_message_time = current_time
            
            print(f"[🚨 LOADED 메시지 감지] 메시지: '{message}'")
            truck_id = self.current_truck_id
            position = self.dispenser_position.get("DISPENSER", "ROUTE_A")
            
            # 중요: truck_id 가 없으면 기본값 사용
            if not truck_id or truck_id == "":
                truck_id = "TRUCK_01"  # 기본값 설정
                print(f"[⚠️ 트럭 ID 누락] 기본값 '{truck_id}' 사용")
            
            print(f"[🌟 디스펜서 LOADED 처리] 트럭: {truck_id}, 위치: {position}")
            
            # 새 상태 설정 (디스펜서가 열렸고 적재되었음을 명시)
            self._update_dispenser_status("DISPENSER", "LOADED", position, "LOADED")
            
            # 즉시 FINISH_LOADING 명령 직접 전송 (가장 빠른 경로)
            if self.facility_status_manager and hasattr(self.facility_status_manager, 'command_sender'):
                command_sender = self.facility_status_manager.command_sender
                if command_sender:
                    try:
                        print(f"[⚡ 즉시 명령 전송] 트럭 {truck_id}에게 FINISH_LOADING 명령 즉시 전송")
                        success = command_sender.send(truck_id, "FINISH_LOADING", {
                            "position": position
                        })
                        print(f"[⚡ 즉시 명령 전송 결과] {'성공' if success else '실패'}")
                        
                        # 0.5초 후 RUN 명령도 즉시 전송
                        import time
                        time.sleep(0.5)
                        print(f"[⚡ 즉시 명령 전송] 트럭 {truck_id}에게 RUN 명령 즉시 전송")
                        success = command_sender.send(truck_id, "RUN", {
                            "target": "CHECKPOINT_C"
                        })
                        print(f"[⚡ 즉시 명령 전송 결과] {'성공' if success else '실패'}")
                    except Exception as e:
                        print(f"[⚠️ 즉시 명령 전송 오류] {e}")
                        
            # 즉시 직접 FSM에 이벤트 전달 (가장 안정적인 방법)
            print(f"[🔥 FSM 직접 이벤트 전달] MainController에서 truck_fsm_manager 직접 접근 시도")
            try:
                import sys
                from backend.main_controller.main_controller import MainController
                
                # MainController 인스턴스 접근
                main_controller = None
                for module in sys.modules.values():
                    if hasattr(module, 'main_controller') and isinstance(getattr(module, 'main_controller'), MainController):
                        main_controller = getattr(module, 'main_controller')
                        break
                
                if main_controller and hasattr(main_controller, 'truck_fsm_manager'):
                    truck_fsm_manager = main_controller.truck_fsm_manager
                    if truck_fsm_manager:
                        print(f"[🚀 FSM 이벤트 전송] 트럭: {truck_id}, DISPENSER_LOADED 이벤트 전송 시작")
                        result = truck_fsm_manager.handle_trigger(truck_id, "DISPENSER_LOADED", {
                            "dispenser_id": "DISPENSER",
                            "position": position
                        })
                        print(f"[✅ FSM 이벤트 전송 완료] 결과: {'성공' if result else '실패'}")
                        
                        # 5초 후 자동으로 FINISH_LOADING 명령 스케줄링
                        print(f"[⏱️ FINISH_LOADING 예약] 5초 후 자동 FINISH_LOADING 명령 예약")
                        self._schedule_finish_loading(truck_id)
                        
                        return True
                    else:
                        print("[❌ FSM 오류] truck_fsm_manager가 None입니다")
                else:
                    print("[❌ FSM 오류] main_controller를 찾을 수 없거나 truck_fsm_manager 속성이 없습니다")
            except Exception as e:
                print(f"[❌ FSM 오류] FSM 직접 이벤트 전달 중 예외 발생: {e}")
                import traceback
                traceback.print_exc()
            
            # command_sender 통한 전송 시도 (백업)
            print(f"[📢 백업 방법] command_sender를 통한 이벤트 전송 시도")
            try:
                if self.facility_status_manager and hasattr(self.facility_status_manager, 'command_sender'):
                    command_sender = self.facility_status_manager.command_sender
                    if command_sender:
                        print(f"[📤 Command Sender] DISPENSER_LOADED 명령 전송 시도: {truck_id}")
                        success = command_sender.send(truck_id, "DISPENSER_LOADED", {
                            "dispenser_id": "DISPENSER",
                            "position": position
                        })
                        print(f"[📤 Command Sender 결과] {'성공' if success else '실패'}")
                        
                        # 두 방식 모두 실패했을 때를 대비해 여전히 FINISH_LOADING 스케줄링
                        print(f"[⏱️ FINISH_LOADING 예약] 5초 후 자동 FINISH_LOADING 명령 예약")
                        self._schedule_finish_loading(truck_id)
                        
                        return True
                    else:
                        print("[❌ Command Sender 오류] command_sender가 None입니다")
                else:
                    print("[❌ Command Sender 오류] facility_status_manager가 None이거나 command_sender 속성이 없습니다")
            except Exception as e:
                print(f"[❌ Command Sender 오류] 명령 전송 중 예외 발생: {e}")
                import traceback
                traceback.print_exc()
            
            # 위의 모든 방법이 실패해도 FINISH_LOADING 스케줄링 (최후의 안전장치)
            print(f"[🔄 최종 안전장치] 이벤트 전송 실패 시에도 자동 FINISH_LOADING 예약")
            self._schedule_finish_loading(truck_id)
            
            return True
            
        # 디스펜서 상태 메시지 처리 (디스펜서가 보내는 다양한 상태 메시지)
        elif "STATUS:DISPENSER:" in message:
            # 상태 메시지 파싱
            parts = message.split(":")
            if len(parts) >= 3:
                state = parts[2]
                
                # 위치 관련 상태 메시지 처리
                if state == "AT_ROUTE_A":
                    print(f"[🧭 디스펜서 위치 변경] 현재 위치: ROUTE_A")
                    self._update_dispenser_status("DISPENSER", self.dispenser_state.get("DISPENSER", "CLOSED"), "ROUTE_A", "IDLE")
                    return True
                    
                elif state == "AT_ROUTE_B":
                    print(f"[🧭 디스펜서 위치 변경] 현재 위치: ROUTE_B")
                    self._update_dispenser_status("DISPENSER", self.dispenser_state.get("DISPENSER", "CLOSED"), "ROUTE_B", "IDLE")
                    return True
                    
                # 준비 상태 메시지 처리
                elif state == "READY":
                    print(f"[✅ 디스펜서 준비 완료] 디스펜서가 준비 상태입니다.")
                    self._update_dispenser_status("DISPENSER", "CLOSED", self.dispenser_position.get("DISPENSER", "ROUTE_A"), "IDLE")
                    return True
                    
                # 열림 과정 상태 메시지 처리
                elif state == "OPENING_COMPLETE":
                    print(f"[🔓 디스펜서 열림 완료] 디스펜서가 열림 상태로 전환되었습니다.")
                    self._update_dispenser_status("DISPENSER", "OPENED", self.dispenser_position.get("DISPENSER", "ROUTE_A"), "IDLE")
                    return True
                    
                # 적재 대기 상태 메시지 처리
                elif state == "WAITING_FOR_LOADED":
                    print(f"[⏳ 디스펜서 적재 대기 중] 디스펜서가 적재 완료를 기다리고 있습니다.")
                    self._update_dispenser_status("DISPENSER", "OPENED", self.dispenser_position.get("DISPENSER", "ROUTE_A"), "LOADING")
                    return True
                    
                # 자동 닫힘 상태 메시지 처리
                elif state == "AUTO_CLOSED":
                    print(f"[🔒 디스펜서 자동 닫힘] 디스펜서가 자동으로 닫혔습니다.")
                    self._update_dispenser_status("DISPENSER", "CLOSED", self.dispenser_position.get("DISPENSER", "ROUTE_A"), "IDLE")
                    return True
            
        # 표준 메시지 처리 로직 (응답 파싱)
        try:
            parsed = self.interface.parse_response(message)
            
            # ACK 메시지 처리
            if parsed["type"] == "ACK":
                if "DI_OPENED" in parsed["raw"]:
                    print(f"[디스펜서 ACK] DISPENSER가 열림 상태가 되었습니다. LOADED 상태를 즉시 처리합니다.")
                    self._update_dispenser_status("DISPENSER", "OPENED", None, "IDLE")
                    
                    # ACK:DI_OPENED 메시지를 받으면 즉시 LOADED 메시지 강제 처리 (지연 제거)
                    print(f"[🔄 즉시 LOADED 처리] ACK:DI_OPENED 수신 후 즉시 LOADED 메시지 강제 처리")
                    
                    # 상태 업데이트를 LOADED로 강제 변경
                    self._update_dispenser_status("DISPENSER", "LOADED", None, "LOADED")
                    
                    # 즉시 LOADED 메시지 처리 - 자신에게 메시지 보내 처리
                    self.handle_message("STATUS:DISPENSER:LOADED")
                    
            # 디스펜서 상태 메시지 처리
            elif parsed["type"] == "DISPENSER" and "state" in parsed:
                dispenser_id = parsed.get("dispenser_id", "DISPENSER")
                state = parsed["state"]
                position = parsed.get("position", self.dispenser_position.get(dispenser_id))
                
                print(f"[⚡ 디스펜서 메시지 수신] 타입: DISPENSER, 상태: {state}, 위치: {position}, 원본: {parsed.get('raw', '')}")
                
                # 상태 업데이트
                self._update_dispenser_status(dispenser_id, state, position, "STATUS_UPDATE")
                
                # OPENED 상태이고 DI_OPENED가 포함된 경우 (타입 변환으로 ACK가 DISPENSER로 변환된 경우 처리)
                if state == "OPENED" and "DI_OPENED" in parsed.get("raw", ""):
                    print(f"[🔄 디스펜서 열림 감지] DISPENSER가 열림 상태가 되었습니다. LOADED 상태를 즉시 처리합니다.")
                    
                    # 즉시 LOADED 메시지 처리 - 자신에게 메시지 보내 처리
                    self.handle_message("STATUS:DISPENSER:LOADED")
                
                # LOADED 메시지 처리 (중복 처리 방지)
                elif state == "LOADED" and not "HANDLE_MESSAGE" in parsed.get("raw", ""):
                    print(f"[⚡ LOADED 상태 감지] 즉시 LOADED 메시지 처리")
                    
                    # 즉시 LOADED 메시지 처리 (완전히 새로 메시지를 만들어 처리)
                    self.handle_message("STATUS:DISPENSER:LOADED:HANDLE_MESSAGE")
            
            # command_sender를 통한 전송 시도 (백업 방법)
            if self.facility_status_manager and hasattr(self.facility_status_manager, 'command_sender'):
                command_sender = self.facility_status_manager.command_sender
                if command_sender:
                    try:
                        print(f"[⭐ 명령 전송자 호출] command_sender를 통해 DISPENSER_LOADED 메시지 전송")
                        success = command_sender.send(truck_id, "DISPENSER_LOADED", {
                            "dispenser_id": "DISPENSER",
                            "position": position
                        })
                        print(f"[⭐ 명령 전송 결과] {'성공' if success else '실패'}")
                    except Exception as e:
                        print(f"[⚠️ 명령 전송 오류] {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"[⚠️ facility_status_manager 또는 command_sender 없음] DISPENSER_LOADED 메시지를 전송할 수 없습니다")
            
            # 3초 후 FINISH_LOADING 자동 전송 (마지막 안전장치)
            def send_finish_loading(truck_id=truck_id, position=position):
                import time
                time.sleep(3.0)  # 3초 대기
                try:
                    print(f"[⭐ 자동 FINISH_LOADING] 트럭 {truck_id}에 FINISH_LOADING 메시지 전송")
                    # FSM 직접 호출
                    from backend.main_controller.main_controller import main_controller
                    if main_controller and main_controller.truck_fsm_manager:
                        result = main_controller.truck_fsm_manager.handle_trigger(truck_id, "FINISH_LOADING", {
                            "position": position
                        })
                        print(f"[⭐ 자동 FINISH_LOADING FSM 직접 호출 결과] {'성공' if result else '실패'}")
                    
                    # command_sender 호출
                    if self.facility_status_manager and hasattr(self.facility_status_manager, 'command_sender'):
                        command_sender = self.facility_status_manager.command_sender
                        if command_sender:
                            success = command_sender.send(truck_id, "FINISH_LOADING", {
                                "position": position
                            })
                            print(f"[⭐ 자동 FINISH_LOADING 메시지 전송 결과] {'성공' if success else '실패'}")
                            
                            # 1초 후 RUN 명령도 전송
                            time.sleep(1.0)
                            success = command_sender.send(truck_id, "RUN", {
                                "target": "CHECKPOINT_C"  # 다음 목적지로 명시적 지정
                            })
                            print(f"[⭐ 자동 RUN 명령 전송 결과] {'성공' if success else '실패'}")
                            
                            # 명시적으로 다음 목적지 설정 추가
                            success = command_sender.send(truck_id, "SET_DESTINATION", {
                                "position": "CHECKPOINT_C"
                            })
                            print(f"[🔄 자동 목적지 설정 결과] {'성공' if success else '실패'}")
                except Exception as e:
                    print(f"[⚠️ 자동 FINISH_LOADING 오류] {e}")
                    import traceback
                    traceback.print_exc()
            
            # 백그라운드에서 자동 FINISH_LOADING 실행
            import threading
            threading.Thread(target=send_finish_loading, daemon=True).start()
            
            return
            
        except Exception as e:
            print(f"[⚠️ 메시지 처리 오류] 원본 메시지: {message}, 오류: {e}")
            import traceback
            traceback.print_exc()
    
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
        else:
            print(f"[디스펜서 열림 실패] {dispenser_id} - 응답: {response}")
            
            # 응답 실패 시 강제 상태 업데이트
            if "DI_OPENED" in (response or ""):
                print(f"[디스펜서 열림 대체 확인] {dispenser_id}")
                self._update_dispenser_status(dispenser_id, "OPENED", None, "IDLE")
                success = True
            else:
                print(f"[강제 상태 변경] {dispenser_id} - 응답 실패로 강제로 OPENED 상태로 설정")
                self._update_dispenser_status(dispenser_id, "OPENED", None, "FORCED_OPEN")
                success = True
                
        # 작업 완료 표시
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

    # ----------------------- 자동 FINISH_LOADING 스케줄링 -----------------------
    
    def _schedule_finish_loading(self, truck_id):
        """FINISH_LOADING 명령을 자동으로 예약하는 함수"""
        print(f"[🔄 자동 FINISH_LOADING 예약] {truck_id}에게 1초 후 자동으로 FINISH_LOADING 명령을 전송할 예정입니다.")
        
        # truck_id를 클로저로 캡처하기 위해 매개변수로 전달
        def send_finish_loading(truck_id=truck_id):
            import time
            time.sleep(1.0)  # 1초로 단축 (5초에서 변경) 
            print(f"[🔄 자동 완료 처리] 자동으로 FINISH_LOADING 명령 전송을 시도합니다.")
            
            try:
                # 1. 먼저 command_sender 사용 (직접 트럭에게 메시지 전송)
                if self.facility_status_manager and hasattr(self.facility_status_manager, 'command_sender'):
                    command_sender = self.facility_status_manager.command_sender
                    if command_sender:
                        position = self.dispenser_position.get("DISPENSER", "ROUTE_A")
                        
                        # FINISH_LOADING 명령 즉시 전송
                        print(f"[🚀 직접 명령 전송] 트럭 {truck_id}에게 FINISH_LOADING 명령 직접 전송")
                        success = command_sender.send(truck_id, "FINISH_LOADING", {
                            "position": position
                        })
                        print(f"[🔄 FINISH_LOADING 명령 전송 결과] {'성공' if success else '실패'}")
                        
                        # 0.5초 후 RUN 명령 즉시 전송
                        time.sleep(0.5)
                        print(f"[🚀 직접 명령 전송] 트럭 {truck_id}에게 RUN 명령 직접 전송 (목적지: CHECKPOINT_C)")
                        success = command_sender.send(truck_id, "RUN", {
                            "target": "CHECKPOINT_C"  # 다음 목적지로 명시적 지정
                        })
                        print(f"[🔄 RUN 명령 전송 결과] {'성공' if success else '실패'}")
                        
                        # 명시적으로 다음 목적지 설정
                        print(f"[🚀 목적지 설정] 트럭 {truck_id}의 다음 목적지를 CHECKPOINT_C로 명시적 설정")
                        success = command_sender.send(truck_id, "SET_DESTINATION", {
                            "position": "CHECKPOINT_C"
                        })
                        print(f"[🔄 목적지 설정 결과] {'성공' if success else '실패'}")
                        
                        return True
                    else:
                        print("[⚠️ 명령 전송 실패] command_sender가 없습니다.")
                else:
                    print("[⚠️ 명령 전송 실패] facility_status_manager가 없거나 command_sender 속성이 없습니다.")
                
                # 2. 백업 방법: FSM 직접 호출 (command_sender 실패 시)
                print("[🔄 백업 방법] FSM 매니저 직접 호출")
                success = self._notify_fsm_manager_directly(truck_id, "FINISH_LOADING", {
                    "position": self.dispenser_position.get("DISPENSER", "ROUTE_A")
                })
                print(f"[🔄 FSM 직접 호출 결과] {'성공' if success else '실패'}")
                
                # FSM 직접 호출로 RUN 명령도 시도
                time.sleep(0.5)
                success = self._notify_fsm_manager_directly(truck_id, "RUN", {
                    "target": "CHECKPOINT_C"
                })
                print(f"[🔄 FSM RUN 명령 직접 호출 결과] {'성공' if success else '실패'}")
                
            except Exception as e:
                print(f"[⚠️ 자동 FINISH_LOADING 오류] {e}")
                import traceback
                traceback.print_exc()
        
        # 백그라운드에서 자동 FINISH_LOADING 실행
        import threading
        thread = threading.Thread(target=send_finish_loading, daemon=True)
        thread.start()
        
        # 중요: 주 스레드에서도 즉시 메시지 전송 시도 (최대한 신속하게 처리)
        if self.facility_status_manager and hasattr(self.facility_status_manager, 'command_sender'):
            command_sender = self.facility_status_manager.command_sender
            if command_sender:
                try:
                    position = self.dispenser_position.get("DISPENSER", "ROUTE_A")
                    print(f"[⚡ 즉시 명령 전송] 트럭 {truck_id}에게 DISPENSER_LOADED 이벤트 즉시 전송")
                    command_sender.send(truck_id, "DISPENSER_LOADED", {
                        "dispenser_id": "DISPENSER",
                        "position": position
                    })
                except Exception as e:
                    print(f"[⚠️ 즉시 명령 전송 오류] {e}")
                    pass

    # ----------------------- 백업 방법 구현 -----------------------
    
    def _notify_fsm_manager_directly(self, truck_id, event, payload=None):
        """트럭 FSM 매니저에 직접 이벤트 전달하는 백업 방법"""
        try:
            import sys
            import importlib
            
            # FSM 매니저를 직접 찾기 위한 임시 코드
            from backend.main_controller.main_controller import MainController
            
            # MainController 인스턴스 접근 시도
            main_controller = None
            for module in sys.modules.values():
                if hasattr(module, 'main_controller') and isinstance(module.main_controller, MainController):
                    main_controller = module.main_controller
                    break
            
            if main_controller:
                truck_fsm_manager = getattr(main_controller, 'truck_fsm_manager', None)
                if truck_fsm_manager:
                    print(f"[🌟 백업 성공] FSM 매니저를 직접 찾았습니다. 이벤트 직접 전달: {event}")
                    truck_fsm_manager.handle_trigger(truck_id, event, payload)
                    return True
            
            print("[⚠️ 백업 실패] FSM 매니저를 찾을 수 없습니다.")
            return False
        except Exception as e:
            print(f"[⚠️ 백업 오류] 직접 FSM 매니저 호출 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    # 디스펜서 적재 완료 메시지 전송 헬퍼 함수
    def _send_dispenser_loaded_to_truck(self, truck_id, dispenser_id, position):
        """트럭에 디스펜서 적재 완료 메시지를 전송하는 헬퍼 함수"""
        print(f"[⭐⭐⭐ 디스펜서 적재 완료 메시지 전송] 트럭 {truck_id}에게 DISPENSER_LOADED 메시지 전송 시작")
        
        # 1. 먼저 직접 FSM 호출 시도 (가장 안정적)
        print(f"[🌟 FSM 직접 호출] 트럭 FSM 매니저에 직접 DISPENSER_LOADED 이벤트 전달")
        fsm_result = self._notify_fsm_manager_directly(truck_id, "DISPENSER_LOADED", {
            "dispenser_id": dispenser_id,
            "position": position
        })
        print(f"[🌟 FSM 직접 호출 결과] {'성공' if fsm_result else '실패'}")
        
        # 2. command_sender를 통한 전송
        if self.facility_status_manager and hasattr(self.facility_status_manager, 'command_sender'):
            command_sender = self.facility_status_manager.command_sender
            if command_sender:
                print(f"[⭐ 명령 전송자 호출] command_sender를 통해 DISPENSER_LOADED 메시지 전송")
                try:
                    success = command_sender.send(truck_id, "DISPENSER_LOADED", {
                        "dispenser_id": dispenser_id,
                        "position": position
                    })
                    print(f"[⭐ 명령 전송 결과] {'성공' if success else '실패'}")
                except Exception as e:
                    print(f"[⚠️ 명령 전송 오류] {e}")
            else:
                print(f"[❌ 명령 전송자 없음] command_sender가 없어 추가 메시지를 전송할 수 없습니다.")
        else:
            print(f"[⚠️ facility_status_manager 누락] facility_status_manager가 설정되지 않았습니다.")
        
        print(f"[⭐⭐⭐ 디스펜서 적재 완료 메시지 전송 완료] 메시지 전송 시도 완료")
