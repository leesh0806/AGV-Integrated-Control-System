from .truck_state import TruckState, MissionPhase, TruckContext, Direction
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
        
        # 상태 전이 테이블 확장 - ASSIGNED 상태 관련 처리 추가
        self._add_assigned_state_transitions()
        self._extend_finish_unloading_action()
        
        print("[✅ FSM 매니저 초기화 완료]")
    
    def _add_assigned_state_transitions(self):
        """ASSIGNED 상태와 관련된 전이 추가"""
        # ASSIGNED 상태에서 위치 도착 시 WAITING으로 변경
        self.transition_manager.transitions[(TruckState.ASSIGNED, "ARRIVED")] = {
            "next_state": TruckState.WAITING,
            "action": self.transition_manager._handle_arrival,
            "condition": None
        }
        
        # ASSIGNED 상태에서 ACK_GATE_OPENED 이벤트 시 MOVING으로 변경
        self.transition_manager.transitions[(TruckState.ASSIGNED, "ACK_GATE_OPENED")] = {
            "next_state": TruckState.MOVING, 
            "action": self.transition_manager._handle_gate_opened,
            "condition": None
        }
        
        # ASSIGNED 상태에서도 로딩/언로딩 시작 가능
        self.transition_manager.transitions[(TruckState.ASSIGNED, "START_LOADING")] = {
            "next_state": TruckState.LOADING,
            "action": self.transition_manager._start_loading,
            "condition": self.transition_manager._is_at_loading_area
        }
        
        self.transition_manager.transitions[(TruckState.ASSIGNED, "START_UNLOADING")] = {
            "next_state": TruckState.UNLOADING,
            "action": self.transition_manager._start_unloading,
            "condition": self.transition_manager._is_at_unloading_area
        }
        
        # ASSIGNED 상태에서 로딩/언로딩 완료 처리
        self.transition_manager.transitions[(TruckState.ASSIGNED, "FINISH_LOADING")] = {
            "next_state": TruckState.MOVING,
            "action": self.transition_manager._finish_loading_and_move,
            "condition": None
        }
        
        self.transition_manager.transitions[(TruckState.ASSIGNED, "FINISH_UNLOADING")] = {
            "next_state": TruckState.MOVING,
            "action": self.transition_manager._finish_unloading_and_move,
            "condition": None
        }

        # 미션 취소 처리 전이 추가
        self.transition_manager.transitions[(TruckState.ASSIGNED, "CANCEL_MISSION")] = {
            "next_state": TruckState.IDLE,
            "action": self._handle_mission_cancellation,
            "condition": None
        }
        
        # WAITING 상태에서도 미션 취소 가능
        self.transition_manager.transitions[(TruckState.WAITING, "CANCEL_MISSION")] = {
            "next_state": TruckState.IDLE,
            "action": self._handle_mission_cancellation,
            "condition": None
        }
        
        # MOVING 상태에서도 미션 취소 가능 (로딩 시작 전에만)
        self.transition_manager.transitions[(TruckState.MOVING, "CANCEL_MISSION")] = {
            "next_state": TruckState.IDLE,
            "action": self._handle_mission_cancellation,
            "condition": self._can_cancel_mission
        }
    
    def _extend_finish_unloading_action(self):
        """하역 완료 액션 확장"""
        # 하역 완료 액션에 미션 완료 로직 추가
        original_action = self.transition_manager._finish_unloading_and_move
        
        def extended_action(context, payload):
            # 원래 액션 호출
            original_action(context, payload)
            
            # 방향을 복귀 방향으로 설정
            context.direction = Direction.RETURN
            
            # 추가 로직 (필요시)
            print(f"[언로딩 완료 확장] {context.truck_id}: 방향을 {context.direction.value}로 설정")
            
        # 액션 교체
        self.transition_manager.transitions[(TruckState.UNLOADING, "FINISH_UNLOADING")]["action"] = extended_action

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
        context.direction = Direction.RETURN
        context.target_position = "STANDBY"
        
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {
                "target": context.target_position
            })
            
        return True
        
    def _can_cancel_mission(self, context, payload):
        """미션 취소 가능 여부 확인"""
        # 로딩이 시작되기 전에만 취소 가능
        return (context.mission_phase in [MissionPhase.TO_LOADING, MissionPhase.NONE] and
                context.state != TruckState.LOADING)
    
    def set_commander(self, command_sender):
        """명령 전송자 설정"""
        self.command_sender = command_sender
        self.transition_manager.command_sender = command_sender
        if self.mission_manager:
            self.mission_manager.set_command_sender(command_sender)
        
    def handle_event(self, truck_id, event, payload=None):
        """이벤트 처리"""
        return self.transition_manager.handle_event(truck_id, event, payload)
    
    def send_run(self, truck_id):
        """트럭 주행 명령 전송"""
        if self.command_sender:
            self.command_sender.send(truck_id, "RUN")
    
    def send_stop(self, truck_id):
        """트럭 정지 명령 전송"""
        if self.command_sender:
            self.command_sender.send(truck_id, "STOP")
    
    def handle_trigger(self, truck_id, cmd, payload=None):
        """트럭 트리거 처리 (트럭 메시지에서 호출)"""
        if payload is None:
            payload = {}
            
        try:
            # 트리거 로그 출력
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
                "ACK_GATE_OPENED": "ACK_GATE_OPENED",
                "START_CHARGING": "START_CHARGING",
                "CANCEL_MISSION": "CANCEL_MISSION"  # 미션 취소 명령 추가
            }
            
            # 위치 정보 추출 및 업데이트
            if "position" in payload:
                context = self.transition_manager._get_or_create_context(truck_id)
                context.position = payload["position"]
                
            # ARRIVED 명령 처리
            if cmd == "ARRIVED" and "position" in payload:
                position = payload["position"]
                # 위치 정보 처리
                context = self.transition_manager._get_or_create_context(truck_id)
                old_position = context.position
                context.position = position
                
                # 위치 업데이트 로깅
                print(f"[위치 업데이트] {truck_id}: {old_position} → {position}")
                
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
                        # 미션 없음 메시지 전송
                        self.command_sender.send(truck_id, "NO_MISSION", {
                            "message": "미션이 없습니다. 나중에 다시 시도하세요.",
                            "wait_time": 10  # 30초에서 10초로 줄임
                        })
                        
                        # 트럭이 이미 대기 위치에 있지 않다면, 대기 위치로 이동하도록 명령
                        context = self.transition_manager._get_or_create_context(truck_id)
                        if context.position != "STANDBY":
                            print(f"[대기 명령] 트럭 {truck_id}에 대기 장소로 이동 명령")
                            self.command_sender.send(truck_id, "RUN", {
                                "target": "STANDBY"
                            })
                        else:
                            # 트럭이 이미 STANDBY에 있는 경우 명시적으로 상태 초기화
                            print(f"[대기 상태 유지] 트럭 {truck_id}는 이미 대기 위치에 있고 할당할 미션이 없음")
                            context.state = TruckState.IDLE
                            context.mission_phase = MissionPhase.NONE
                            context.target_position = None
                    
                    # 미션 없음 상태를 반환
                    return False
            
            # 상태 전이 관리자로 이벤트 전달
            event = event_mapping.get(cmd, cmd)
            return self.transition_manager.handle_event(truck_id, event, payload)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[❌ FSM 트리거 오류] {e}")
            return False
    
    def update_truck_status(self, truck_id, position, battery_level, is_charging=False):
        """트럭 상태 업데이트"""
        # 컨텍스트 가져오기
        context = self.transition_manager._get_or_create_context(truck_id)
        
        # 위치 변경 감지
        if position and context.position != position:
            old_position = context.position
            # 위치 업데이트 및 이벤트 처리
            self.transition_manager.handle_position_update(truck_id, position)
            
        # 배터리 상태 업데이트
        if battery_level is not None:
            context.battery_level = battery_level
            context.is_charging = is_charging
    
    def get_all_truck_statuses(self):
        """모든 트럭 상태 가져오기"""
        result = {}
        for truck_id, context in self.transition_manager.contexts.items():
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
    
    def _open_gate_and_log(self, gate_id, truck_id):
        """게이트 열림 로깅 및 명령 전송"""
        return self.transition_manager._open_gate_and_log(gate_id, truck_id)
        
    def _close_gate_and_log(self, gate_id, truck_id):
        """게이트 닫기 로깅 및 명령 전송"""
        return self.transition_manager._close_gate_and_log(gate_id, truck_id)
        
    def get_truck_context(self, truck_id):
        """트럭 컨텍스트 가져오기"""
        return self.transition_manager._get_or_create_context(truck_id)
        
    def get_all_truck_contexts(self):
        """모든 트럭 컨텍스트 가져오기"""
        return self.transition_manager.contexts
        
    def handle_checkpoint_arrival(self, truck_id, checkpoint_id):
        """체크포인트 도착 처리 (더 이상 사용하지 않음 - 호환성 유지)"""
        print(f"[경고] handle_checkpoint_arrival은 더 이상 직접 호출하지 마세요. handle_trigger('ARRIVED_AT_{checkpoint_id}')를 대신 사용하세요.")
        # 위치 정보 처리 - 직접 ARRIVED 이벤트로 변환
        context = self.transition_manager._get_or_create_context(truck_id)
        old_position = context.position
        context.position = checkpoint_id
        
        # 위치 업데이트 로깅
        print(f"[위치 업데이트] {truck_id}: {old_position} → {checkpoint_id}")
        
        # 직접 ARRIVED 이벤트로 전달
        return self.transition_manager.handle_event(truck_id, "ARRIVED", {"position": checkpoint_id})

    def get_state(self, truck_id):
        """트럭 상태 조회"""
        context = self.transition_manager._get_or_create_context(truck_id)
        return context.state 