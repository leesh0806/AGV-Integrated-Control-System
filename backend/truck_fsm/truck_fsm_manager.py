from .truck_state import TruckState, MissionPhase, TruckContext, Direction
from .truck_fsm import TruckFSM
import time


class TruckFSMManager:
    def __init__(self, gate_controller, mission_manager, belt_controller=None, dispenser_controller=None, truck_status_manager=None):
        self.gate_controller = gate_controller
        self.mission_manager = mission_manager
        self.belt_controller = belt_controller
        self.dispenser_controller = dispenser_controller
        self.truck_status_manager = truck_status_manager
        self.command_sender = None
        self.fsm = TruckFSM(
            gate_controller=gate_controller,
            belt_controller=belt_controller,
            dispenser_controller=dispenser_controller,
            mission_manager=mission_manager
        )
        self.BATTERY_THRESHOLD = 30
        self.BATTERY_FULL = 100
        
        # 체크포인트 명령 중복 처리 방지를 위한 변수 추가
        self.last_checkpoint_commands = {}  # {truck_id: {"position": position, "timestamp": timestamp}}
        
        print("[✅ FSM 매니저 초기화 완료]")
    
    # -------------------------------------------------------------------------------

    # command_sender 설정
    def set_commander(self, command_sender):
        self.command_sender = command_sender
        self.fsm.command_sender = command_sender
        
        # 새로 추가: command_sender에 truck_status_manager 설정
        if hasattr(command_sender, 'set_truck_status_manager') and self.truck_status_manager:
            # 상태 관리자가 이미 설정되어 있는지 확인 (is not으로 명시적 ID 비교)
            if not hasattr(command_sender, 'truck_status_manager') or command_sender.truck_status_manager is not self.truck_status_manager:
                command_sender.set_truck_status_manager(self.truck_status_manager)
        
        if self.mission_manager:
            self.mission_manager.set_command_sender(command_sender)

    # -------------------------------------------------------------------------------

    # 이벤트 처리
    def handle_event(self, truck_id, event, payload=None):
        return self.fsm.handle_event(truck_id, event, payload)

    # 트리거 처리
    def handle_trigger(self, truck_id, cmd, payload=None):
        if payload is None:
            payload = {}
            
        try:
            # 트리거 로그 출력
            print(f"[FSM] 트리거: {truck_id}, 명령: {cmd}")
            
            # time 모듈 문제 해결을 위해 명시적 import 추가
            import time as timer
            
            # 기존 로직과 호환되는 이벤트 매핑
            event_mapping = {
                "ASSIGN_MISSION": "ASSIGN_MISSION",
                "START_LOADING": "START_LOADING",
                "FINISH_LOADING": "FINISH_LOADING",
                "START_UNLOADING": "START_UNLOADING",
                "FINISH_UNLOADING": "FINISH_UNLOADING",
                "EMERGENCY_TRIGGERED": "EMERGENCY_TRIGGERED",
                "RESET": "RESET",
                "FINISH_CHARGING": "FINISH_CHARGING",
                "ACK_GATE_OPENED": "ACK_GATE_OPENED",
                "START_CHARGING": "START_CHARGING",
                "CANCEL_MISSION": "CANCEL_MISSION"  # 미션 취소 명령 추가
            }
            
            # 위치 정보 추출 및 업데이트
            if "position" in payload:
                context = self.fsm._get_or_create_context(truck_id)
                context.position = payload["position"]
                
            # ARRIVED 명령 처리
            if cmd == "ARRIVED" and "position" in payload:
                position = payload["position"]
                # 위치 정보 처리
                context = self.fsm._get_or_create_context(truck_id)
                old_position = context.position
                context.position = position
                
                # 위치 업데이트 로깅
                print(f"[위치 업데이트] {truck_id}: {old_position} → {position}")
                
                # 위치가 LOAD_A 또는 LOAD_B인 경우 적재 시작 명령 자동 전송
                if position in ["LOAD_A", "LOAD_B"]:
                    print(f"[🚨 적재 위치 자동 감지] {truck_id}가 {position}에 도착")
                    
                    # 현재 트럭의 미션 정보 확인
                    loading_target = getattr(context, 'loading_target', None)
                    mission_id = getattr(context, 'mission_id', None)
                    
                    # 미션이 있고, 현재 위치가 미션의 목적지인 경우에만 정지 및 적재 시작
                    if mission_id and (loading_target == position or loading_target is None):
                        print(f"[✅ 미션 목적지 확인] {truck_id}의 미션 목적지({loading_target})와 현재 위치({position})가 일치")
                        
                        # 트럭 ID를 디스펜서 컨트롤러에 전역 변수로 저장
                        if self.dispenser_controller:
                            self.dispenser_controller.current_truck_id = truck_id
                            print(f"[🔄 트럭 ID 설정] 디스펜서 컨트롤러에 트럭 ID '{truck_id}' 설정")
                        
                        # 먼저 트럭 정지 명령 전송
                        if self.command_sender:
                            print(f"[🛑 STOP 명령 전송] {truck_id}에게 정지 명령 전송")
                            self.command_sender.send(truck_id, "STOP")
                            timer.sleep(0.5)  # 잠시 대기
                        
                        # 적재 시작 명령 전송
                        if self.command_sender:
                            print(f"[📤 START_LOADING 명령 전송] {truck_id}에게 적재 시작 명령 전송")
                            self.command_sender.send(truck_id, "START_LOADING", {"position": position})
                            timer.sleep(0.5)
                        
                        # 명시적으로 FSM 상태 변경
                        print(f"[🔄 FSM 상태 변경] {truck_id}: START_LOADING 이벤트 처리")
                        self.fsm.handle_event(truck_id, "START_LOADING", {"position": position})
                        
                        # 디스펜서 직접 제어
                        if self.dispenser_controller:
                            print(f"[🔄 디스펜서 제어 시작] {position}에서 디스펜서 제어")
                            try:
                                if position == "LOAD_A":
                                    success = self.dispenser_controller.send_command("DISPENSER", "LOC_ROUTE_A")
                                    print(f"[디스펜서 경로 설정 결과] ROUTE_A: {'성공' if success else '실패'}")
                                elif position == "LOAD_B":
                                    success = self.dispenser_controller.send_command("DISPENSER", "LOC_ROUTE_B")
                                    print(f"[디스펜서 경로 설정 결과] ROUTE_B: {'성공' if success else '실패'}")
                                    
                                # 잠시 대기 후 디스펜서 열기
                                timer.sleep(1.0)
                                success = self.dispenser_controller.send_command("DISPENSER", "OPEN")
                                print(f"[디스펜서 열기 결과] {'성공' if success else '실패'}")
                            except Exception as e:
                                print(f"[⚠️ 디스펜서 제어 오류] {e}")
                        else:
                            print(f"[⚠️ 디스펜서 컨트롤러 없음] 디스펜서 제어 불가")
                        
                        # 중요: 적재 위치에 도착했을 때는 다음 RUN 명령을 자동으로 보내지 않음
                        # DISPENSER_LOADED 이벤트를 받아야만 다음 이동 명령이 전송됨
                        print(f"[🔒 자동 이동 대기] {truck_id}가 {position}에서 디스펜서 적재 완료(DISPENSER_LOADED) 이벤트를 기다리는 중...")
                        return True
                    else:
                        # 미션이 없거나 현재 위치가 미션의 목적지가 아닌 경우
                        print(f"[⚠️ 미션 불일치] {truck_id}의 위치({position})에서 정지하지 않음. 미션 ID: {mission_id}, 목적지: {loading_target}")
                        print(f"[🚚 계속 이동] {truck_id}는 목적지가 아닌 적재 위치를 지나 계속 이동합니다.")
                
            # ASSIGN_MISSION 명령이고 미션 ID가 지정되지 않은 경우 미션 매니저에서 대기 중인 미션 찾기
            if cmd == "ASSIGN_MISSION" and "mission_id" not in payload and self.mission_manager:
                waiting_missions = self.mission_manager.get_waiting_missions()
                
                # 대기 중인 미션이 있다면 가장 오래된 미션 할당
                if waiting_missions:
                    mission = waiting_missions[0]  # 가장 처음 생성된 대기 미션
                    
                    # 페이로드에 미션 정보 추가
                    payload["mission_id"] = mission.mission_id
                    payload["source"] = mission.source
                    
                    print(f"[미션 자동 할당] 트럭 {truck_id}에 대기 미션 {mission.mission_id} 할당")
                    
                    # 미션 할당
                    assignment_result = self.mission_manager.assign_mission_to_truck(mission.mission_id, truck_id)
                    if not assignment_result:
                        print(f"[⚠️ 미션 할당 실패] 트럭 {truck_id}에 미션 {mission.mission_id} 할당에 실패했습니다.")
                        # 미션 할당 실패 시 페이로드에서 미션 정보 제거
                        if "mission_id" in payload:
                            del payload["mission_id"]
                        if "source" in payload:
                            del payload["source"]
                else:
                    # 미션이 없는 경우 대기 명령 전송
                    print(f"[미션 없음] 트럭 {truck_id}에 할당할 미션이 없음")
                    
                    if self.command_sender:
                        # 트럭이 이미 대기 위치에 있는 경우 충전 시작
                        context = self.fsm._get_or_create_context(truck_id)
                        if context.position == "STANDBY":
                            # 배터리 상태 확인 - 미션이 없을 때는 100% 충전이 아니면 항상 충전 시작
                            if context.battery_level < self.BATTERY_FULL:
                                print(f"[자동 충전 시작] 트럭 {truck_id}는 대기 위치에 있고 미션이 없으며 배터리({context.battery_level}%)가 100% 아니므로 충전을 시작합니다.")
                                
                                # 명시적으로 IDLE 상태로 변경
                                context.state = TruckState.IDLE
                                context.mission_phase = MissionPhase.NONE
                                context.target_position = None
                                
                                # 충전 이벤트 트리거
                                self.fsm.handle_event(truck_id, "START_CHARGING")
                                
                                # 충전 명령 전송
                                self.command_sender.send(truck_id, "START_CHARGING", {
                                    "message": "미션이 없고 배터리가 100%가 아니므로 충전을 시작합니다."
                                })
                            else:
                                print(f"[충전 불필요] 트럭 {truck_id}는 대기 위치에 있고 배터리가 이미 완충(100%)되었습니다. 대기 상태를 유지합니다.")
                                
                                # 명시적으로 IDLE 상태로 변경
                                context.state = TruckState.IDLE
                                context.mission_phase = MissionPhase.NONE
                                context.target_position = None
                                
                                # 상태 업데이트 명령만 전송
                                self.command_sender.send(truck_id, "NO_MISSION", {
                                    "message": "미션이 없고 배터리가 이미 완충되었으므로 대기 상태를 유지합니다."
                                })
                                
                            return True
                        else:
                            # 트럭이 대기 위치에 있지 않다면, 대기 위치로 이동하도록 명령
                            print(f"[대기 명령] 트럭 {truck_id}에 대기 장소로 이동 명령")
                            self.command_sender.send(truck_id, "NO_MISSION", {
                                "message": "미션이 없습니다. 나중에 다시 시도하세요.",
                                "wait_time": 10  # 30초에서 10초로 줄임
                            })
                            self.command_sender.send(truck_id, "RUN", {
                                "target": "STANDBY"
                            })
                    else:
                        # 명령 전송 객체가 없는 경우
                        print(f"[대기 상태 유지] 트럭 {truck_id}는 이미 대기 위치에 있고 할당할 미션이 없음")
                        context.state = TruckState.IDLE
                        context.mission_phase = MissionPhase.NONE
                        context.target_position = None
                    
                    # 미션 없음 상태를 반환
                    return False
            
            # DISPENSER_LOADED 이벤트를 명시적으로 처리
            elif cmd == "DISPENSER_LOADED":
                print(f"[⭐ DISPENSER_LOADED 받음] {truck_id}: 디스펜서 적재 완료 신호 수신")
                context = self.fsm._get_or_create_context(truck_id)
                
                # 현재 상태 로깅
                print(f"[⭐ 트럭 상태 확인] {truck_id}: 상태={context.state}, 현재 위치={context.position}, 미션 단계={context.mission_phase}")
                
                # 먼저 이벤트를 FSM에 전달하여 상태 전이 발생시키기
                print(f"[⭐ FSM 이벤트 전달] {truck_id}: DISPENSER_LOADED 이벤트를 FSM에 전달")
                self.fsm.handle_event(truck_id, "DISPENSER_LOADED", payload)
                
                # 트럭의 현재 위치 확인 및 보정
                current_position = context.position
                
                # 디스펜서 위치와 트럭 위치 매핑을 위한 명확한 변환
                if current_position in ["ROUTE_A", "ROUTE_B"]:
                    # 디스펜서 위치를 트럭 위치로 변환
                    old_position = current_position
                    if current_position == "ROUTE_A":
                        current_position = "LOAD_A"
                    elif current_position == "ROUTE_B":
                        current_position = "LOAD_B"
                    print(f"[🔄 위치 매핑] 디스펜서 위치 {old_position}를 트럭 위치 {current_position}로 변환")
                elif not current_position or current_position not in ["LOAD_A", "LOAD_B"]:
                    # 현재 디스펜서 위치를 확인하여 적절한 위치 설정
                    if self.dispenser_controller and hasattr(self.dispenser_controller, 'current_position'):
                        dispenser_position = self.dispenser_controller.current_position
                        if dispenser_position == "ROUTE_A":
                            current_position = "LOAD_A"
                            print(f"[🔄 위치 매핑] 디스펜서 위치 {dispenser_position}를 트럭 위치 {current_position}로 변환")
                        elif dispenser_position == "ROUTE_B":
                            current_position = "LOAD_B"
                            print(f"[🔄 위치 매핑] 디스펜서 위치 {dispenser_position}를 트럭 위치 {current_position}로 변환")
                        else:
                            current_position = "LOAD_A"  # 기본값
                            print(f"[⚠️ 위치 보정] 알 수 없는 디스펜서 위치({dispenser_position})를 기본 위치 {current_position}로 설정")
                    else:
                        # 기본 위치를 LOAD_A로 설정 (안전장치)
                        current_position = "LOAD_A"
                        print(f"[⚠️ 위치 보정] 적재 위치 정보가 없어 기본 위치 {current_position}로 설정")
                
                # 위치 보정 필요한 경우만 메시지 출력
                if current_position != context.position:
                    print(f"[⚠️ 위치 보정] {truck_id}의 현재 위치({context.position})가 적재 위치가 아닙니다.")
                    print(f"[⚠️ 위치 설정] 적재 위치를 {current_position}로 설정합니다.")
                    
                    # 컨텍스트 위치 업데이트
                    context.position = current_position
                
                # 즉시 FINISH_LOADING 명령도 직접 전송 (강제)
                print(f"[🚀 강제 FINISH_LOADING] {truck_id}: FINISH_LOADING 명령 강제 전송 (위치: {current_position})")
                success = False
                try:
                    if hasattr(self, 'command_sender') and self.command_sender:
                        # 최대 3회 재시도
                        max_retries = 3
                        for attempt in range(max_retries):
                            success = self.command_sender.send(truck_id, "FINISH_LOADING", {
                                "position": current_position  # 명시적으로 현재 위치 전달
                            })
                            if success:
                                print(f"[🚀 강제 FINISH_LOADING 결과] 성공 (시도: {attempt+1}/{max_retries})")
                                break
                            else:
                                print(f"[⚠️ FINISH_LOADING 실패] 재시도 중... ({attempt+1}/{max_retries})")
                                import time
                                time.sleep(0.5)  # 재시도 전 짧은 대기
                        
                        # RUN 명령은 FINISH_LOADING이 성공했을 때만 전송
                        if success:
                            # 0.5초 후 RUN 명령도 강제 전송
                            import time
                            time.sleep(0.5)
                            run_success = self.command_sender.send(truck_id, "RUN", {
                                "target": "CHECKPOINT_C"
                            })
                            print(f"[🚀 강제 RUN 명령 결과] {'성공' if run_success else '실패'}")
                            
                            # RUN 실패 시 재시도
                            if not run_success:
                                time.sleep(0.5)
                                run_success = self.command_sender.send(truck_id, "RUN", {})
                                print(f"[🚀 강제 RUN 재시도 결과] {'성공' if run_success else '실패'}")
                    else:
                        print(f"[⚠️ 명령 전송 실패] command_sender가 설정되지 않았습니다.")
                except Exception as e:
                    print(f"[⚠️ 명령 전송 오류] {e}")
                    import traceback
                    traceback.print_exc()
                
                # 디스펜서 닫기 명령
                if self.dispenser_controller:
                    try:
                        print(f"[🔄 디스펜서 닫기] 적재 완료로 디스펜서 닫기")
                        close_success = self.dispenser_controller.send_command("DISPENSER", "CLOSE")
                        print(f"[디스펜서 닫기 결과] {'성공' if close_success else '실패'}")
                        
                        # 디스펜서가 완전히 닫힐 때까지 충분히 대기
                        wait_time = 2.0  # 2초 대기 시간(3초에서 단축)
                        print(f"[디스펜서 닫힘 대기] {truck_id}: {wait_time}초 대기 중...")
                        import time
                        time.sleep(wait_time)
                        print(f"[디스펜서 닫힘 완료] {truck_id}: 대기 완료, 이동 준비됨")
                    except Exception as e:
                        print(f"[⚠️ 디스펜서 닫기 오류] {e}")
                        # 오류 발생 시에도 최소한의 대기 시간 제공
                        import time
                        time.sleep(1.0)
                else:
                    print(f"[⚠️ 디스펜서 컨트롤러 없음] 디스펜서 제어 불가")
                    
                # 상태 LOADED로 직접 변경 - loading → loaded
                context.state = TruckState.LOADED
                print(f"[⭐ 트럭 상태 변경] {truck_id}: 상태를 LOADED로 직접 변경")
                
                # 다음 목적지 설정 - CHECKPOINT_C로 명시적 설정
                next_target = "CHECKPOINT_C"
                context.target_position = next_target
                print(f"[🚀 다음 목적지 설정] {truck_id}: 다음 목적지를 {next_target}로 설정")
                
                # 해당 이벤트는 처리 완료
                return True
            
            # FINISH_UNLOADING 이벤트 처리 추가
            elif cmd == "FINISH_UNLOADING":
                print(f"[✅ FINISH_UNLOADING 받음] {truck_id}: 하역 완료 신호 수신")
                context = self.fsm._get_or_create_context(truck_id)
                
                # 현재 상태 로깅
                print(f"[✅ 트럭 상태 확인] {truck_id}: 상태={context.state}, 현재 위치={context.position}, 미션 단계={context.mission_phase}")
                
                # FSM에 이벤트 전달
                self.fsm.handle_event(truck_id, "FINISH_UNLOADING", payload)
                
                # 트럭의 현재 위치 확인
                current_position = context.position
                if not current_position or current_position != "BELT":
                    print(f"[⚠️ 위치 확인] {truck_id}의 현재 위치({current_position})가 하역 위치(BELT)가 아닙니다.")
                    print(f"[⚠️ 위치 가정] 하역 위치를 BELT로 가정합니다.")
                    current_position = "BELT"
                    context.position = current_position
                
                # 미션 단계 업데이트
                if context.mission_phase != MissionPhase.COMPLETED:
                    old_phase = context.mission_phase
                    context.mission_phase = MissionPhase.COMPLETED
                    print(f"[✅ 미션 단계 변경] {truck_id}: {old_phase} → {context.mission_phase}")
                
                # 미션 완료 처리
                mission_id = context.mission_id
                if mission_id and self.mission_manager:
                    # 미션 완료 표시
                    self.mission_manager.complete_mission(mission_id)
                    print(f"[✅ 미션 완료] {truck_id}: 미션 {mission_id} 완료됨")
                
                # 상태 변경 (적재완료→공차)
                if context.state != TruckState.IDLE:
                    old_state = context.state
                    context.state = TruckState.IDLE
                    print(f"[✅ 상태 변경] {truck_id}: {old_state} → {context.state}")
                
                # 대기 장소(STANDBY)로 돌아가는 RUN 명령 전송
                if self.command_sender:
                    try:
                        # 잠시 대기 후 RUN 명령 전송
                        import time
                        time.sleep(0.5)
                        
                        # 대기 위치(STANDBY)로 이동 명령
                        print(f"[🚀 자동 RUN 명령 전송] {truck_id}: 하역 완료 후 STANDBY로 이동 명령 전송")
                        
                        # 최대 3회 재시도
                        max_retries = 3
                        for attempt in range(max_retries):
                            run_success = self.command_sender.send(truck_id, "RUN", {
                                "target": "STANDBY"
                            })
                            
                            if run_success:
                                print(f"[🚀 RUN 명령 성공] {truck_id}에게 STANDBY로 이동 명령 전송 성공 (시도: {attempt+1}/{max_retries})")
                                break
                            else:
                                print(f"[⚠️ RUN 명령 실패] {attempt+1}번째 시도 실패, 재시도 중...")
                                time.sleep(0.5)
                        
                        if not run_success:
                            print(f"[⚠️ 경고] {truck_id}에게 RUN 명령 전송 실패. 이동이 지연될 수 있습니다.")
                    except Exception as e:
                        print(f"[⚠️ RUN 명령 전송 오류] {e}")
                else:
                    print(f"[⚠️ 명령 전송 실패] command_sender가 설정되지 않았습니다.")
                
                # ACK 전송
                if self.command_sender:
                    self.command_sender.send(truck_id, "ACK", {
                        "cmd": "FINISH_UNLOADING", 
                        "status": "SUCCESS"
                    })
                
                # 처리 완료
                return True
            
            # START_UNLOADING 이벤트 처리 추가
            elif cmd == "START_UNLOADING":
                print(f"[✅ START_UNLOADING 받음] {truck_id}: 하역 시작 신호 수신")
                context = self.fsm._get_or_create_context(truck_id)
                
                # 현재 상태 로깅
                print(f"[✅ 트럭 상태 확인] {truck_id}: 상태={context.state}, 현재 위치={context.position}, 미션 단계={context.mission_phase}")
                
                # 벨트 컨트롤러가 있으면 벨트 시작
                if self.belt_controller:
                    try:
                        print(f"[🔄 벨트 시작] BELT 작동 시작")
                        # BeltController는 start_belt 메서드가 없고 send_command 메서드를 사용해야 함
                        belt_success = self.belt_controller.send_command("BELT", "RUN")
                        print(f"[벨트 시작 결과] {'성공' if belt_success else '실패'}")
                    except Exception as e:
                        print(f"[⚠️ 벨트 시작 오류] {e}")
                
                # FSM에 이벤트 전달
                self.fsm.handle_event(truck_id, "START_UNLOADING", payload)
                
                # 벨트 자동 정지 로직 제거 - 벨트 정지는 벨트에서 통보받음
                
                # ACK 전송
                if self.command_sender:
                    self.command_sender.send(truck_id, "ACK", {
                        "cmd": "START_UNLOADING", 
                        "status": "SUCCESS"
                    })
                
                # 처리 완료
                return True
            
            # 상태 전이 관리자로 이벤트 전달
            event = event_mapping.get(cmd, cmd)
            return self.fsm.handle_event(truck_id, event, payload)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[❌ FSM 트리거 오류] {e}")
            return False

    # -------------------------------------------------------------------------------

    # 주행 명령 전송
    def send_run(self, truck_id):
        if self.command_sender:
            self.command_sender.send(truck_id, "RUN")
    
    # 정지 명령 전송
    def send_stop(self, truck_id):
        if self.command_sender:
            self.command_sender.send(truck_id, "STOP")

    # -------------------------------------------------------------------------------   

    # 트럭 상태 업데이트
    def update_truck_status(self, truck_id, position, battery_level, is_charging=False):
        # 컨텍스트 가져오기
        context = self.fsm._get_or_create_context(truck_id)
        
        # 위치 변경 감지
        if position and context.position != position:
            old_position = context.position
            # 위치 업데이트 및 이벤트 처리
            self.fsm.handle_position_update(truck_id, position)
            
        # 배터리 상태 업데이트
        if battery_level is not None:
            context.battery_level = battery_level
            context.is_charging = is_charging

    # -------------------------------------------------------------------------------

    # 모든 트럭 상태 가져오기
    def get_all_truck_statuses(self):
        result = {}
        for truck_id, context in self.fsm.contexts.items():
            result[truck_id] = {
                "state": context.state.value,
                "position": context.position,
                "mission_id": context.mission_id,
                "mission_phase": context.mission_phase.value if context.mission_phase else None,
                "battery": {
                    "level": context.battery_level,
                    "is_charging": context.is_charging
                },
                "direction": context.direction.value if hasattr(context, 'direction') else 'UNKNOWN'
            }
        return result
    
    # 트럭 컨텍스트 가져오기
    def get_truck_context(self, truck_id):
        return self.fsm._get_or_create_context(truck_id)

    # 모든 트럭 컨텍스트 가져오기
    def get_all_truck_contexts(self):
        return self.fsm.contexts

    # 트럭 상태 조회
    def get_state(self, truck_id):
        context = self.fsm._get_or_create_context(truck_id)
        return context.state 

    def _handle_mission_cancellation(self, context, payload):
        """미션 취소 처리"""
        if not context.mission_id:
            print(f"[미션 취소 실패] {context.truck_id}: 취소할 미션이 없음")
            return False
            
        mission_id = context.mission_id
        print(f"[미션 취소] {context.truck_id}: 미션 {mission_id} 취소")
        
        # 미션 매니저에 취소 통보
        if self.mission_manager:
            self.mission_manager.cancel_mission(mission_id)
        
        # 상태 초기화
        context.mission_id = None
        context.mission_phase = MissionPhase.NONE
        
        # 트럭 정지 명령
        if self.command_sender:
            self.command_sender.send(context.truck_id, "STOP")
        
        # 대기 장소로 복귀 명령
        context.direction = Direction.CLOCKWISE  # 시계 방향으로 유지
        context.target_position = "STANDBY"
        
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {
                "target": context.target_position
            })
            
        return True 

    def handle_message(self, msg: dict):
        sender = msg.get("sender", "")
        cmd = msg.get("cmd", "")
        payload = msg.get("payload", {})
        
        print(f"[FSM 트리거] 트럭: {sender}, 명령: {cmd}")
        
        # time 모듈 문제 해결을 위해 명시적 import 추가
        import time as timer
        
        # 위치 정보 확인 (ARRIVED 명령 등에서)
        position = payload.get("position", "")
        
        # 체크포인트 명령 중복 필터링
        if cmd == "ARRIVED" and position.startswith("CHECKPOINT_"):
            current_time = timer.time()
            
            # 이전 명령 정보 가져오기
            last_command = self.last_checkpoint_commands.get(sender, {})
            last_position = last_command.get("position")
            last_time = last_command.get("timestamp", 0)
            
            # 동일한 체크포인트에 대해 1초 이내에 반복된 명령인 경우 필터링
            if last_position == position and (current_time - last_time) < 1.0:
                print(f"[⚠️ 중복 명령 필터링] {sender}의 {position} 도착 신호가 중복되어 무시됨 (간격: {current_time - last_time:.2f}초)")
                return True
            
            # 명령 정보 업데이트
            self.last_checkpoint_commands[sender] = {
                "position": position, 
                "timestamp": current_time
            }
        
        # 추가 디버깅: 적재 위치 도착 시 무조건 적재 시작 명령 전송
        if cmd == "ARRIVED" and position in ["LOAD_A", "LOAD_B"]:
            print(f"[🚨 강제 적재 시작 테스트] {sender}가 {position}에 도착함")
            
            # 현재 트럭의 미션 정보 확인
            context = self.fsm._get_or_create_context(sender)
            loading_target = getattr(context, 'loading_target', None)
            mission_id = getattr(context, 'mission_id', None)
            
            # 미션이 있고, 현재 위치가 미션의 목적지인 경우에만 정지 및 적재 시작
            if mission_id and (loading_target == position or loading_target is None):
                print(f"[✅ 미션 목적지 확인] {sender}의 미션 목적지({loading_target})와 현재 위치({position})가 일치")
                
                # 적재 위치에 도착한 경우 무조건 STOP 명령 전송
                if self.command_sender:
                    print(f"[🚨 강제 STOP 명령 전송] {sender}에게 정지 명령 전송")
                    self.command_sender.send(sender, "STOP")
                    timer.sleep(0.5)  # 잠시 대기
                    
                    # 적재 시작 명령 전송
                    print(f"[🚨 강제 START_LOADING 명령 전송] {sender}에게 적재 시작 명령 전송")
                    self.command_sender.send(sender, "START_LOADING", {"position": position})
                    timer.sleep(1.0)  # 프로세스를 위한 대기
                    
                    # 디스펜서 직접 제어
                    if self.dispenser_controller:
                        print(f"[🚨 강제 디스펜서 제어 시작] {position}에서 디스펜서 제어")
                        if position == "LOAD_A":
                            success = self.dispenser_controller.send_command("DISPENSER", "LOC_ROUTE_A")
                            print(f"[🚨 디스펜서 경로 설정 결과] ROUTE_A: {'성공' if success else '실패'}")
                        elif position == "LOAD_B":
                            success = self.dispenser_controller.send_command("DISPENSER", "LOC_ROUTE_B")
                            print(f"[🚨 디스펜서 경로 설정 결과] ROUTE_B: {'성공' if success else '실패'}")
                            
                        # 잠시 대기 후 디스펜서 열기
                        timer.sleep(1.0)
                        success = self.dispenser_controller.send_command("DISPENSER", "OPEN")
                        print(f"[🚨 디스펜서 열기 결과] {'성공' if success else '실패'}")
                    else:
                        print(f"[🚨 디스펜서 컨트롤러 없음] 디스펜서 제어 불가")
                    
                    # 중요: 적재 위치에서는 다음 RUN 명령을 자동으로 보내지 않음
                    # DISPENSER_LOADED 이벤트를 받아야만 다음 이동 명령이 전송됨
                    print(f"[🔒 자동 이동 중단] {sender}가 {position}에서 디스펜서 적재 완료(DISPENSER_LOADED) 이벤트를 기다리는 중...")
                    return True
            else:
                # 미션이 없거나 현재 위치가 미션의 목적지가 아닌 경우
                print(f"[⚠️ 미션 불일치] {sender}의 위치({position})에서 정지하지 않음. 미션 ID: {mission_id}, 목적지: {loading_target}")
                print(f"[🚚 계속 이동] {sender}는 목적지가 아닌 적재 위치를 지나 계속 이동합니다.")
        
        # FSM 이벤트 처리
        return self.fsm.handle_event(sender, cmd, payload) 

    def _open_gate_and_log(self, gate_id, truck_id):
        success = False
        
        print(f"[🔓 게이트 열기 시도] {gate_id} ← by {truck_id}")
        
        if self.gate_controller:
            success = self.gate_controller.open_gate(gate_id)
            if success:
                print(f"[🔓 GATE OPEN] {gate_id} ← by {truck_id}")
        else:
            # 테스트 모드에서는 성공으로 처리
            print(f"[🔓 GATE OPEN 시뮬레이션] {gate_id} ← by {truck_id} (게이트 컨트롤러 없음)")
            success = True
                
        # 트럭에 게이트 열림 알림 전송 (성공 여부와 상관없이 알림)
        if self.command_sender:
            print(f"[📤 게이트 열림 알림] {truck_id}에게 GATE_OPENED 메시지 전송 (gate_id: {gate_id})")
            gate_open_success = self.command_sender.send(truck_id, "GATE_OPENED", {"gate_id": gate_id})
            
            # 게이트 열림 후 잠시 대기 (트럭이 열림 메시지를 처리할 시간 제공)
            import time
            time.sleep(0.5)
            
            # 게이트 열림 후 자동으로 RUN 명령도 전송 - 최대 3회 재시도
            print(f"[📤 자동 RUN 명령 전송] {truck_id}에게 게이트 열림 후 RUN 명령 전송")
            run_success = False
            
            for attempt in range(3):
                run_success = self.command_sender.send(truck_id, "RUN", {})
                if run_success:
                    print(f"[📤 RUN 명령 성공] {truck_id}에게 {attempt+1}번째 시도에 성공")
                    break
                else:
                    print(f"[⚠️ RUN 명령 실패] {attempt+1}번째 시도 실패, 재시도 중...")
                    time.sleep(0.5)
            
            if not run_success:
                print(f"[⚠️ 경고] {truck_id}에게 RUN 명령 전송 실패. 이동이 지연될 수 있습니다.")
        else:
            print(f"[⚠️ 경고] command_sender가 없어 GATE_OPENED/RUN 메시지를 전송할 수 없습니다.")
            
        return success 