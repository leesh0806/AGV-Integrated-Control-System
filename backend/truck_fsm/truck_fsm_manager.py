from .truck_state import TruckState, MissionPhase, TruckContext, Direction
from .state_transition_manager import StateTransitionManager


class TruckFSMManager:
    def __init__(self, gate_controller, mission_manager, belt_controller=None, truck_status_manager=None):
        self.gate_controller = gate_controller
        self.mission_manager = mission_manager
        self.belt_controller = belt_controller
        self.truck_status_manager = truck_status_manager
        self.command_sender = None
        self.transition_manager = StateTransitionManager(
            gate_controller=gate_controller,
            belt_controller=belt_controller,
            mission_manager=mission_manager
        )
        self.BATTERY_THRESHOLD = 30
        self.BATTERY_FULL = 100
        
        print("[✅ FSM 매니저 초기화 완료]")
    

    # -------------------------------------------------------------------------------

    # command_sender 설정
    def set_commander(self, command_sender):
        self.command_sender = command_sender
        self.transition_manager.command_sender = command_sender
        if self.mission_manager:
            self.mission_manager.set_command_sender(command_sender)

    # -------------------------------------------------------------------------------

    # 이벤트 처리
    def handle_event(self, truck_id, event, payload=None):
        return self.transition_manager.handle_event(truck_id, event, payload)

    # 트리거 처리
    def handle_trigger(self, truck_id, cmd, payload=None):
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
                        # 트럭이 이미 대기 위치에 있는 경우 충전 시작
                        context = self.transition_manager._get_or_create_context(truck_id)
                        if context.position == "STANDBY":
                            print(f"[자동 충전 시작] 트럭 {truck_id}는 대기 위치에 있고 미션이 없어 충전을 시작합니다.")
                            
                            # 명시적으로 IDLE 상태로 변경
                            context.state = TruckState.IDLE
                            context.mission_phase = MissionPhase.NONE
                            context.target_position = None
                            
                            # 충전 이벤트 트리거
                            self.transition_manager.handle_event(truck_id, "START_CHARGING")
                            
                            # 충전 명령 전송
                            self.command_sender.send(truck_id, "START_CHARGING", {
                                "message": "미션이 없어 충전을 시작합니다."
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
            
            # 상태 전이 관리자로 이벤트 전달
            event = event_mapping.get(cmd, cmd)
            return self.transition_manager.handle_event(truck_id, event, payload)
            
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

    # -------------------------------------------------------------------------------

    # 모든 트럭 상태 가져오기
    def get_all_truck_statuses(self):
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
    
    # 트럭 컨텍스트 가져오기
    def get_truck_context(self, truck_id):
        return self.transition_manager._get_or_create_context(truck_id)

    # 모든 트럭 컨텍스트 가져오기
    def get_all_truck_contexts(self):
        return self.transition_manager.contexts

    # 트럭 상태 조회
    def get_state(self, truck_id):
        context = self.transition_manager._get_or_create_context(truck_id)
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