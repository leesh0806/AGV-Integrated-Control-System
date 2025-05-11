from .truck_state import TruckState, MissionPhase, TruckContext
from .state_transition_manager import StateTransitionManager


class TruckFSMManager:
    """트럭 FSM 관리자"""
    def __init__(self, gate_controller, mission_manager, belt_controller=None, truck_status_manager=None):
        self.gate_controller = gate_controller
        self.mission_manager = mission_manager
        self.belt_controller = belt_controller
        self.truck_status_manager = truck_status_manager
        self.command_sender = None
        
        # 상태 전이 관리자 생성
        self.transition_manager = StateTransitionManager(
            gate_controller=gate_controller,
            belt_controller=belt_controller,
            mission_manager=mission_manager
        )
        
        # 배터리 관련 상수
        self.BATTERY_THRESHOLD = 30
        self.BATTERY_FULL = 100
        
        print("[✅ FSM 매니저 초기화 완료]")
    
    def set_commander(self, commander):
        """명령 전송 객체 설정"""
        self.command_sender = commander
        self.transition_manager.command_sender = commander
        print(f"[✅ FSM 매니저에 명령 전송 객체 설정됨]")
    
    def get_state(self, truck_id):
        """트럭 상태 조회"""
        # 트럭 상태 DB에서 상태 조회
        if self.truck_status_manager:
            # FSM 상태 가져오기
            fsm_state_str = self.truck_status_manager.get_fsm_state(truck_id)
            
            try:
                # truck_state.py의 TruckState로 변환
                return TruckState[fsm_state_str]
            except (KeyError, ValueError):
                # 이전 형식의 TruckState로 변환 시도
                from .truck_state_enum import TruckState as OldTruckState
                try:
                    # 이전 TruckState에 있는 경우
                    old_state = OldTruckState[fsm_state_str]
                    # 상태 매핑
                    state_mapping = {
                        OldTruckState.IDLE: TruckState.IDLE,
                        OldTruckState.MOVE_TO_GATE_FOR_LOAD: TruckState.MOVING,
                        OldTruckState.WAIT_GATE_OPEN_FOR_LOAD: TruckState.WAITING,
                        OldTruckState.MOVE_TO_LOAD: TruckState.MOVING,
                        OldTruckState.WAIT_LOAD: TruckState.WAITING,
                        OldTruckState.LOADING: TruckState.LOADING,
                        OldTruckState.MOVE_TO_GATE_FOR_UNLOAD: TruckState.MOVING,
                        OldTruckState.WAIT_GATE_OPEN_FOR_UNLOAD: TruckState.WAITING,
                        OldTruckState.MOVE_TO_UNLOAD: TruckState.MOVING,
                        OldTruckState.WAIT_UNLOAD: TruckState.WAITING,
                        OldTruckState.UNLOADING: TruckState.UNLOADING,
                        OldTruckState.MOVE_TO_STANDBY: TruckState.MOVING,
                        OldTruckState.WAIT_NEXT_MISSION: TruckState.IDLE,
                        OldTruckState.CHARGING: TruckState.CHARGING,
                        OldTruckState.EMERGENCY_STOP: TruckState.EMERGENCY
                    }
                    return state_mapping.get(old_state, TruckState.IDLE)
                except (KeyError, ValueError):
                    print(f"[DEBUG] 유효하지 않은 FSM 상태 문자열: {fsm_state_str}, 기본값 IDLE로 설정")
                    return TruckState.IDLE
        
        # 컨텍스트에서 상태 조회
        context = self.transition_manager._get_or_create_context(truck_id)
        return context.state
    
    def set_state(self, truck_id, new_state):
        """트럭 상태 설정"""
        context = self.transition_manager._get_or_create_context(truck_id)
        prev_state = context.state
        
        # 새 상태 설정
        if isinstance(new_state, TruckState):
            context.state = new_state
        else:
            # 문자열이나 이전 TruckState를 새 TruckState로 변환
            from .truck_state_enum import TruckState as OldTruckState
            
            if isinstance(new_state, OldTruckState):
                # 이전 TruckState 매핑
                state_mapping = {
                    OldTruckState.IDLE: TruckState.IDLE,
                    OldTruckState.MOVE_TO_GATE_FOR_LOAD: TruckState.MOVING,
                    OldTruckState.WAIT_GATE_OPEN_FOR_LOAD: TruckState.WAITING,
                    OldTruckState.MOVE_TO_LOAD: TruckState.MOVING,
                    OldTruckState.WAIT_LOAD: TruckState.WAITING,
                    OldTruckState.LOADING: TruckState.LOADING,
                    OldTruckState.MOVE_TO_GATE_FOR_UNLOAD: TruckState.MOVING,
                    OldTruckState.WAIT_GATE_OPEN_FOR_UNLOAD: TruckState.WAITING,
                    OldTruckState.MOVE_TO_UNLOAD: TruckState.MOVING,
                    OldTruckState.WAIT_UNLOAD: TruckState.WAITING,
                    OldTruckState.UNLOADING: TruckState.UNLOADING,
                    OldTruckState.MOVE_TO_STANDBY: TruckState.MOVING,
                    OldTruckState.WAIT_NEXT_MISSION: TruckState.IDLE,
                    OldTruckState.CHARGING: TruckState.CHARGING,
                    OldTruckState.EMERGENCY_STOP: TruckState.EMERGENCY
                }
                context.state = state_mapping.get(new_state, TruckState.IDLE)
            else:
                # 문자열을 Enum으로 변환
                try:
                    context.state = TruckState[str(new_state)]
                except (KeyError, ValueError):
                    print(f"[경고] 유효하지 않은 상태: {new_state}, 현재 상태 유지")
                    return
        
        # 상태 변경 로깅
        print(f"[FSM] {truck_id}: {prev_state} → {context.state}")
        
        # 트럭 상태 DB에 동기화
        if self.truck_status_manager:
            state_str = context.state.name
            self.truck_status_manager.set_fsm_state(truck_id, state_str)
    
    def send_run(self, truck_id):
        """트럭 주행 명령 전송"""
        if self.command_sender:
            self.command_sender.send(truck_id, "RUN")
    
    def send_stop(self, truck_id):
        """트럭 정지 명령 전송"""
        if self.command_sender:
            self.command_sender.send(truck_id, "STOP")
    
    def handle_trigger(self, truck_id, cmd, payload=None):
        """트리거 처리"""
        try:
            if payload is None:
                payload = {}
                
            print(f"[FSM] 트리거: {truck_id}, 명령: {cmd}")
            
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
                "ACK_GATE_OPENED": "ACK_GATE_OPENED"
            }
            
            # 위치 정보 추출 및 업데이트
            if "position" in payload:
                context = self.transition_manager._get_or_create_context(truck_id)
                context.position = payload["position"]
            
            # ARRIVED_AT_ 접두사가 있는 명령 처리
            if cmd.startswith("ARRIVED_AT_"):
                position = cmd.replace("ARRIVED_AT_", "")
                payload["position"] = position
                
                # 트럭 상태 DB에 위치 정보 업데이트
                if self.truck_status_manager:
                    # 위치 정보와 run_state 업데이트
                    current_status = self.truck_status_manager.get_truck_status(truck_id)
                    run_state = current_status.get("position", {}).get("run_state", "IDLE")
                    self.truck_status_manager.update_position(truck_id, position, run_state)
                
                # 위치 정보 처리
                return self.transition_manager.handle_position_update(truck_id, position, payload)
            
            # 레거시 명령을 새 이벤트 형식으로 매핑
            if cmd in event_mapping:
                event = event_mapping[cmd]
                
                # 미션 ID가 없고 ASSIGN_MISSION 이벤트인 경우, 미션 매니저에서 대기 중인 미션 가져오기
                if event == "ASSIGN_MISSION" and "mission_id" not in payload and self.mission_manager:
                    waiting_missions = self.mission_manager.get_waiting_missions()
                    if waiting_missions:
                        next_mission = waiting_missions[0]
                        payload["mission_id"] = next_mission.mission_id
                        payload["source"] = next_mission.source or "LOAD_A"
                
                # 트럭 상태 DB에 배터리 정보 업데이트
                if "battery_level" in payload and self.truck_status_manager:
                    battery_level = payload["battery_level"]
                    is_charging = cmd == "START_CHARGING"
                    self.truck_status_manager.update_battery(truck_id, battery_level, is_charging)
                    
                    # 컨텍스트에도 배터리 정보 업데이트
                    context = self.transition_manager._get_or_create_context(truck_id)
                    context.battery_level = battery_level
                    context.is_charging = is_charging
                
                # 이벤트 처리
                return self.transition_manager.handle_event(truck_id, event, payload)
            
            # 미매핑된 명령은 로그만 출력
            print(f"[경고] 매핑되지 않은 명령: {cmd}")
            return False
            
        except Exception as e:
            print(f"[FSM] 오류 발생: {e}")
            return False
    
    def check_battery(self, truck_id):
        """배터리 상태 확인"""
        if self.truck_status_manager:
            truck_status = self.truck_status_manager.get_truck_status(truck_id)
            battery_level = truck_status['battery']['level']
            is_charging = truck_status['battery']['is_charging']
            
            print(f"[🔋 배터리 체크] {truck_id}의 배터리: {battery_level}% (충전중: {is_charging})")
            
            # 컨텍스트에 배터리 정보 업데이트
            context = self.transition_manager._get_or_create_context(truck_id)
            context.battery_level = battery_level
            context.is_charging = is_charging
            
            # 배터리가 임계값 이하이고 충전 중이 아니면
            if battery_level <= self.BATTERY_THRESHOLD and not is_charging:
                print(f"[⚠️ 경고] {truck_id}의 배터리가 낮음: {battery_level}% <= {self.BATTERY_THRESHOLD}%")
                return False
                
            # 배터리가 100%이고 충전 중인 경우 - 충전 상태 해제
            if battery_level >= self.BATTERY_FULL and is_charging:
                print(f"[✅ 완료] {truck_id}의 배터리 충전 완료: {battery_level}%")
                self.truck_status_manager.update_battery(truck_id, battery_level, False)
                context.is_charging = False
                
                # 충전 완료 트리거 발생
                print(f"[🔋 충전 완료] {truck_id}의 충전이 완료되었습니다. FINISH_CHARGING 트리거 발생")
                self.handle_trigger(truck_id, "FINISH_CHARGING", {})
                
            return True
        return False
    
    def _open_gate_and_log(self, gate_id, truck_id):
        """게이트 열림 로깅 및 명령 전송"""
        return self.transition_manager._open_gate_and_log(gate_id, truck_id)
        
    def _close_gate_and_log(self, gate_id, truck_id):
        """게이트 닫기 로깅 및 명령 전송"""
        return self.transition_manager._close_gate_and_log(gate_id, truck_id) 