from .truck_state import TruckState, MissionPhase, TruckContext
from datetime import datetime


class StateTransitionManager:
    """FSM 상태 전이 관리 클래스"""
    def __init__(self, command_sender=None, gate_controller=None, belt_controller=None, mission_manager=None):
        self.command_sender = command_sender
        self.gate_controller = gate_controller
        self.belt_controller = belt_controller
        self.mission_manager = mission_manager
        self.contexts = {}  # truck_id -> TruckContext
        
        # 상태 전이 테이블 초기화
        self.transitions = self._init_transitions()
        
        # 배터리 관련 값
        self.BATTERY_THRESHOLD = 30
        self.BATTERY_FULL = 100
        
    def _init_transitions(self):
        """상태 전이 테이블 정의"""
        return {
            # (현재 상태, 이벤트) -> (다음 상태, 액션 함수, 조건 함수)
            
            # IDLE 상태 전이
            (TruckState.IDLE, "ASSIGN_MISSION"): {
                "next_state": TruckState.ASSIGNED,
                "action": self._assign_mission,
                "condition": self._can_accept_mission
            },
            
            # ASSIGNED 상태 전이
            (TruckState.ASSIGNED, "START_MOVING"): {
                "next_state": TruckState.MOVING,
                "action": self._start_moving,
                "condition": None
            },
            
            # MOVING 상태 전이
            (TruckState.MOVING, "ARRIVED"): {
                "next_state": TruckState.WAITING,
                "action": self._handle_arrival,
                "condition": None
            },
            
            # WAITING 상태 전이
            (TruckState.WAITING, "START_LOADING"): {
                "next_state": TruckState.LOADING,
                "action": self._start_loading,
                "condition": self._is_at_loading_area
            },
            (TruckState.WAITING, "START_UNLOADING"): {
                "next_state": TruckState.UNLOADING,
                "action": self._start_unloading,
                "condition": self._is_at_unloading_area
            },
            (TruckState.WAITING, "RESUME_MOVING"): {
                "next_state": TruckState.MOVING,
                "action": self._resume_moving,
                "condition": None
            },
            (TruckState.WAITING, "ACK_GATE_OPENED"): {
                "next_state": TruckState.MOVING,
                "action": self._handle_gate_opened,
                "condition": None
            },
            
            # LOADING 상태 전이
            (TruckState.LOADING, "FINISH_LOADING"): {
                "next_state": TruckState.MOVING,
                "action": self._finish_loading_and_move,
                "condition": None
            },
            
            # UNLOADING 상태 전이
            (TruckState.UNLOADING, "FINISH_UNLOADING"): {
                "next_state": TruckState.MOVING,
                "action": self._finish_unloading_and_move,
                "condition": None
            },
            
            # 충전 관련 전이
            (TruckState.IDLE, "START_CHARGING"): {
                "next_state": TruckState.CHARGING,
                "action": self._start_charging,
                "condition": self._needs_charging
            },
            (TruckState.CHARGING, "FINISH_CHARGING"): {
                "next_state": TruckState.IDLE,
                "action": self._finish_charging,
                "condition": self._is_fully_charged
            },
            
            # 비상 상태 전이
            (None, "EMERGENCY_TRIGGERED"): {
                "next_state": TruckState.EMERGENCY,
                "action": self._handle_emergency,
                "condition": None
            },
            (TruckState.EMERGENCY, "RESET"): {
                "next_state": TruckState.IDLE,
                "action": self._reset_from_emergency,
                "condition": None
            }
        }
        
    def _get_or_create_context(self, truck_id):
        """컨텍스트 가져오기 또는 생성"""
        if truck_id not in self.contexts:
            self.contexts[truck_id] = TruckContext(truck_id)
        return self.contexts[truck_id]
        
    def handle_event(self, truck_id, event, payload=None):
        """이벤트 처리 및 상태 전이"""
        if payload is None:
            payload = {}
            
        context = self._get_or_create_context(truck_id)
        current_state = context.state
        
        # 이벤트 처리 시간 기록
        context.last_update_time = datetime.now()
        
        # 이벤트 로깅
        print(f"[이벤트 수신] 트럭: {truck_id}, 이벤트: {event}, 상태: {current_state}")
        
        # 위치 업데이트가 있는 경우
        if event == "ARRIVED" and "position" in payload:
            new_position = payload["position"]
            old_position = context.position
            context.position = new_position
            print(f"[위치 업데이트] {truck_id}: {old_position} → {new_position}")
            
            # 위치에 따른 미션 단계 업데이트
            self._update_mission_phase_by_position(context)
        
        # 상태 전이 찾기
        key = (current_state, event)
        global_key = (None, event)
        
        transition = self.transitions.get(key) or self.transitions.get(global_key)
        
        if transition:
            # 조건 검사
            condition_fn = transition.get("condition")
            if condition_fn and not condition_fn(context, payload):
                print(f"[조건 불만족] {truck_id}: {current_state}, {event}")
                return False
            
            # 상태 전이 실행
            next_state = transition["next_state"]
            action_fn = transition.get("action")
            
            # 상태 변경 전 로깅
            print(f"[상태 전이] {truck_id}: {current_state} → {next_state} (이벤트: {event})")
            
            # 상태 업데이트
            context.state = next_state
            
            # 액션 실행
            if action_fn:
                action_fn(context, payload)
            
            return True
        else:
            print(f"[상태 전이 없음] {truck_id}: {current_state}, {event}")
            return False
    
    def _update_mission_phase_by_position(self, context):
        """위치에 따른 미션 단계 업데이트"""
        position = context.position
        
        # 위치별 미션 단계 매핑
        position_to_phase = {
            "CHECKPOINT_A": MissionPhase.TO_LOADING,
            "GATE_A": MissionPhase.TO_LOADING,
            "LOAD_A": MissionPhase.AT_LOADING,
            "LOAD_B": MissionPhase.AT_LOADING,
            "CHECKPOINT_C": MissionPhase.TO_UNLOADING,
            "GATE_B": MissionPhase.TO_UNLOADING,
            "CHECKPOINT_D": MissionPhase.TO_UNLOADING,
            "BELT": MissionPhase.AT_UNLOADING,
            "STANDBY": MissionPhase.RETURNING if context.mission_id else MissionPhase.NONE
        }
        
        if position in position_to_phase:
            old_phase = context.mission_phase
            new_phase = position_to_phase[position]
            
            if old_phase != new_phase:
                context.mission_phase = new_phase
                print(f"[미션 단계 업데이트] {context.truck_id}: {old_phase} → {new_phase}")
                
                # 다음 목표 위치 업데이트
                self._update_target_position(context)
    
    def _update_target_position(self, context):
        """미션 단계에 따른 다음 목표 위치 설정"""
        phase = context.mission_phase
        
        if phase == MissionPhase.TO_LOADING:
            if context.position == "CHECKPOINT_A":
                context.target_position = "GATE_A"
            elif context.position == "GATE_A":
                # 미션 정보에 따라 적재 위치 결정 (기본값 LOAD_A)
                context.target_position = "LOAD_A"
        elif phase == MissionPhase.AT_LOADING:
            context.target_position = "CHECKPOINT_C"
        elif phase == MissionPhase.TO_UNLOADING:
            if context.position == "CHECKPOINT_C":
                context.target_position = "GATE_B"
            elif context.position == "GATE_B":
                context.target_position = "CHECKPOINT_D"
            elif context.position == "CHECKPOINT_D":
                context.target_position = "BELT"
        elif phase == MissionPhase.AT_UNLOADING:
            context.target_position = "STANDBY"
        elif phase == MissionPhase.RETURNING:
            context.target_position = "STANDBY"
        else:
            context.target_position = None
        
        if context.target_position:
            print(f"[목표 위치 업데이트] {context.truck_id}: 다음 목표 → {context.target_position}")
            
    # -------------------------------- 액션 메서드 --------------------------------
            
    def _assign_mission(self, context, payload):
        """미션 할당 처리"""
        mission_id = payload.get("mission_id")
        source = payload.get("source", "LOAD_A")
        
        context.mission_id = mission_id
        context.mission_phase = MissionPhase.TO_LOADING
        context.target_position = "CHECKPOINT_A"  # 첫 목표는 게이트 A 체크포인트
        
        print(f"[미션 할당] {context.truck_id}: 미션 {mission_id}, 출발지 {source}")
        
        # 트럭에 이동 명령 전송
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {
                "mission_id": mission_id,
                "target": context.target_position
            })
    
    def _start_moving(self, context, payload):
        """이동 시작 처리"""
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {
                "target": context.target_position
            })
    
    def _handle_arrival(self, context, payload):
        """도착 처리 - 위치에 따라 다른 액션 수행"""
        position = context.position
        
        # 위치별 처리
        if position == "CHECKPOINT_A":
            # 게이트 열기 요청
            if self.gate_controller:
                self._open_gate_and_log("GATE_A", context.truck_id)
                
        elif position == "CHECKPOINT_C":
            # 게이트 열기 요청
            if self.gate_controller:
                self._open_gate_and_log("GATE_B", context.truck_id)
                
        elif position in ["LOAD_A", "LOAD_B"]:
            # 트럭 정지
            if self.command_sender:
                self.command_sender.send(context.truck_id, "STOP")
                
        elif position == "BELT":
            # 트럭 정지
            if self.command_sender:
                self.command_sender.send(context.truck_id, "STOP")
                
        elif position == "STANDBY":
            # 미션 완료 처리
            if context.mission_phase == MissionPhase.RETURNING and context.mission_id:
                print(f"[미션 완료] {context.truck_id}: 미션 {context.mission_id} 완료 및 대기 상태로 전환")
                
                # 미션 매니저로 미션 완료 처리
                if self.mission_manager and context.mission_id:
                    self.mission_manager.complete_mission(context.mission_id)
                    
                context.mission_phase = MissionPhase.COMPLETED
                context.mission_id = None
                
                # 다음 미션 할당 시도
                self.handle_event(context.truck_id, "ASSIGN_MISSION", {})
    
    def _handle_gate_opened(self, context, payload):
        """게이트 열림 처리"""
        # 다음 위치로 이동 명령
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {
                "target": context.target_position
            })
    
    def _start_loading(self, context, payload):
        """적재 작업 시작 처리"""
        print(f"[적재 시작] {context.truck_id}: 위치 {context.position}에서 적재 작업 시작")
        # 필요한 경우 추가 액션 수행
    
    def _finish_loading_and_move(self, context, payload):
        """적재 완료 및 이동 처리"""
        print(f"[적재 완료] {context.truck_id}: 적재 작업 완료, 다음 목표 {context.target_position}으로 이동")
        
        # 다음 단계 업데이트
        context.mission_phase = MissionPhase.TO_UNLOADING
        context.target_position = "CHECKPOINT_C"
        
        # 이동 명령 전송
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {
                "target": context.target_position
            })
    
    def _start_unloading(self, context, payload):
        """하차 작업 시작 처리"""
        print(f"[하차 시작] {context.truck_id}: 위치 {context.position}에서 하차 작업 시작")
        
        # 벨트 작동 명령 전송
        if self.belt_controller:
            print(f"[벨트 작동] {context.truck_id} → 벨트에 RUN 명령 전송")
            self.belt_controller.send_command("BELT", "RUN")
    
    def _finish_unloading_and_move(self, context, payload):
        """하차 완료 및 이동 처리"""
        print(f"[하차 완료] {context.truck_id}: 하차 작업 완료, 대기장소로 복귀")
        
        # 다음 단계 업데이트
        context.mission_phase = MissionPhase.RETURNING
        context.target_position = "STANDBY"
        
        # 이동 명령 전송
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {
                "target": context.target_position
            })
    
    def _resume_moving(self, context, payload):
        """이동 재개 처리"""
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {
                "target": context.target_position
            })
    
    def _start_charging(self, context, payload):
        """충전 시작 처리"""
        context.is_charging = True
        print(f"[충전 시작] {context.truck_id}: 배터리 레벨 {context.battery_level}%")
        
        if self.command_sender:
            self.command_sender.send(context.truck_id, "START_CHARGING")
    
    def _finish_charging(self, context, payload):
        """충전 완료 처리"""
        context.is_charging = False
        print(f"[충전 완료] {context.truck_id}: 배터리 레벨 {context.battery_level}%")
        
        if self.command_sender:
            self.command_sender.send(context.truck_id, "CHARGING_COMPLETED")
            
        # 완충 후 미션 할당 시도
        self.handle_event(context.truck_id, "ASSIGN_MISSION", {})
    
    def _handle_emergency(self, context, payload):
        """비상 상황 처리"""
        print(f"[⚠️ 비상 상황] {context.truck_id}: 비상 정지")
        
        # 트럭 정지 명령
        if self.command_sender:
            self.command_sender.send(context.truck_id, "STOP")
        
        # 벨트 정지 명령
        if self.belt_controller:
            self.belt_controller.send_command("BELT", "EMRSTOP")
    
    def _reset_from_emergency(self, context, payload):
        """비상 상황 해제 처리"""
        print(f"[🔄 비상 해제] {context.truck_id}: 기본 상태로 복귀")
        
        # 미션 취소 처리
        if context.mission_id and self.mission_manager:
            self.mission_manager.cancel_mission(context.mission_id)
            context.mission_id = None
            context.mission_phase = MissionPhase.NONE
    
    # -------------------------------- 조건 메서드 --------------------------------
    
    def _can_accept_mission(self, context, payload):
        """미션 수락 가능 여부 확인"""
        # 이미 미션이 할당되어 있으면 수락 불가
        if context.mission_id is not None:
            print(f"[미션 거부] {context.truck_id}: 이미 미션 {context.mission_id}이 할당되어 있음")
            return False
        
        # 충전 중이면 수락 불가
        if context.is_charging:
            print(f"[미션 거부] {context.truck_id}: 충전 중")
            return False
        
        # 배터리가 부족하면 수락 불가
        if context.battery_level <= self.BATTERY_THRESHOLD:
            print(f"[미션 거부] {context.truck_id}: 배터리 부족 ({context.battery_level}%)")
            return False
        
        # 비상 상태면 수락 불가
        if context.state == TruckState.EMERGENCY:
            print(f"[미션 거부] {context.truck_id}: 비상 상태")
            return False
            
        return True
    
    def _is_at_loading_area(self, context, payload):
        """적재 위치에 있는지 확인"""
        return context.position in ["LOAD_A", "LOAD_B"]
    
    def _is_at_unloading_area(self, context, payload):
        """하역 위치에 있는지 확인"""
        return context.position == "BELT"
    
    def _needs_charging(self, context, payload):
        """충전 필요 여부 확인"""
        return context.battery_level <= self.BATTERY_THRESHOLD
    
    def _is_fully_charged(self, context, payload):
        """완전 충전 여부 확인"""
        return context.battery_level >= self.BATTERY_FULL
    
    # -------------------------------- 게이트 제어 메서드 --------------------------------
    
    def _open_gate_and_log(self, gate_id, truck_id):
        """게이트 열기"""
        if self.gate_controller:
            success = self.gate_controller.open_gate(gate_id)
            if success:
                print(f"[🔓 GATE OPEN] {gate_id} ← by {truck_id}")
                if self.command_sender:
                    self.command_sender.send(truck_id, "GATE_OPENED", {"gate_id": gate_id})
            return success
        return False
    
    def _close_gate_and_log(self, gate_id, truck_id):
        """게이트 닫기"""
        if self.gate_controller:
            success = self.gate_controller.close_gate(gate_id)
            if success:
                print(f"[🔒 GATE CLOSE] {gate_id} ← by {truck_id}")
                if self.command_sender:
                    self.command_sender.send(truck_id, "GATE_CLOSED", {"gate_id": gate_id})
            return success
        return False
    
    # -------------------------------- 위치 관리 메서드 --------------------------------
    
    def handle_position_update(self, truck_id, new_position, payload=None):
        """위치 업데이트 처리"""
        if payload is None:
            payload = {}
            
        context = self._get_or_create_context(truck_id)
        old_position = context.position
        
        # 위치 업데이트
        context.position = new_position
        print(f"[위치 변경] {truck_id}: {old_position} → {new_position}")
        
        # 위치 기반 이벤트 생성
        payload["position"] = new_position
        self.handle_event(truck_id, "ARRIVED", payload)
        
        # 위치와 상태의 일관성 검증
        self._validate_position_state_consistency(context)
        
        return True
    
    def _validate_position_state_consistency(self, context):
        """위치와 상태의 일관성 검증"""
        position = context.position
        state = context.state
        
        # 특정 상태에서 예상되는 위치 정의
        state_to_expected_positions = {
            TruckState.LOADING: ["LOAD_A", "LOAD_B"],
            TruckState.UNLOADING: ["BELT"],
            TruckState.WAITING: ["CHECKPOINT_A", "GATE_A", "CHECKPOINT_C", "GATE_B", "BELT", "LOAD_A", "LOAD_B"]
        }
        
        # 위치와 상태가 일치하지 않는 경우 감지
        if (state in state_to_expected_positions and 
                position not in state_to_expected_positions[state]):
            print(f"[⚠️ 불일치 감지] {context.truck_id}: 상태 {state}와 위치 {position}이 일치하지 않음")
            
            # 자동 복구 로직
            if position in ["LOAD_A", "LOAD_B"] and state != TruckState.LOADING:
                # 적재 위치에 있는데 LOADING 상태가 아니면, WAITING 상태로 변경
                suggested_state = TruckState.WAITING
                print(f"[🔄 자동 조정] {context.truck_id}: 상태를 {suggested_state}로 변경")
                context.state = suggested_state
            
            elif position == "BELT" and state != TruckState.UNLOADING:
                # 하역 위치에 있는데 UNLOADING 상태가 아니면, WAITING 상태로 변경
                suggested_state = TruckState.WAITING
                print(f"[🔄 자동 조정] {context.truck_id}: 상태를 {suggested_state}로 변경")
                context.state = suggested_state 