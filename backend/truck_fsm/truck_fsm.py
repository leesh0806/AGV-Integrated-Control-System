from .truck_state import TruckState, MissionPhase, TruckContext, Direction
from datetime import datetime
import time


class TruckFSM:
    def __init__(self, command_sender=None, gate_controller=None, belt_controller=None, mission_manager=None):
        self.command_sender = command_sender
        self.gate_controller = gate_controller
        self.belt_controller = belt_controller
        self.mission_manager = mission_manager
        self.contexts = {}
        self.transitions = self._init_transitions()
        self._add_assigned_state_transitions()
        self._extend_finish_unloading_action()
        self.BATTERY_THRESHOLD = 30
        self.BATTERY_FULL = 100
        self.checkpoint_gate_mapping = {
            Direction.CLOCKWISE: {
                "CHECKPOINT_A": {"open": "GATE_A", "close": None},
                "CHECKPOINT_B": {"open": None, "close": "GATE_A"},
                "CHECKPOINT_C": {"open": "GATE_B", "close": None},
                "CHECKPOINT_D": {"open": None, "close": "GATE_B"},
            },
            Direction.COUNTERCLOCKWISE: {
                "CHECKPOINT_D": {"open": "GATE_B", "close": None},
                "CHECKPOINT_C": {"open": None, "close": "GATE_B"},
                "CHECKPOINT_B": {"open": "GATE_A", "close": None},
                "CHECKPOINT_A": {"open": None, "close": "GATE_A"},
            }
        }
        self.direction_transition_points = {
            "STANDBY": Direction.CLOCKWISE,       # 대기 장소에 도착 후 시계방향(정상 흐름)으로 전환
            "LOAD_A": Direction.CLOCKWISE,        # 적재 완료 후 시계방향 유지
            "LOAD_B": Direction.CLOCKWISE,        # 적재 완료 후 시계방향 유지
            "BELT": Direction.CLOCKWISE,          # 하역 완료 후에도 시계방향 유지
        }
        
    # -------------------------------------------------------------------------------   

    # 상태 전이 테이블 정의
    def _init_transitions(self):
        return {
            # (현재 상태, 이벤트) -> (다음 상태, 액션 함수, 조건 함수)
            
            # IDLE 상태 전이
            (TruckState.IDLE, "ASSIGN_MISSION"): {
                "next_state": TruckState.ASSIGNED,
                "action": self._assign_mission,
                "condition": self._can_accept_mission
            },
            (TruckState.IDLE, "FINISH_LOADING"): {  # IDLE 상태에서 FINISH_LOADING 이벤트 처리 추가
                "next_state": TruckState.MOVING,
                "action": self._finish_loading_and_move,
                "condition": None
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
    
    # -------------------------------------------------------------------------------   

    # 컨텍스트 가져오기 또는 생성
    def _get_or_create_context(self, truck_id):
        if truck_id not in self.contexts:
            self.contexts[truck_id] = TruckContext(truck_id)
        return self.contexts[truck_id]

    # -------------------------------------------------------------------------------   

    # 이벤트 처리
    def handle_event(self, truck_id, event, payload=None):
        if payload is None: payload = {}
            
        context = self._get_or_create_context(truck_id)
        current_state = context.state
        context.last_update_time = datetime.now()
        print(f"[이벤트 수신] 트럭: {truck_id}, 이벤트: {event}, 상태: {current_state}")
        
        # FINISH_LOADING 특별 처리 - 상태와 상관없이 RUN 명령 보내기
        if event == "FINISH_LOADING":
            print(f"[특별 처리] {truck_id}: FINISH_LOADING 이벤트 수신, 상태와 무관하게 처리")
            
            # 상태 전이 시도 (성공 여부 확인)
            key = (current_state, event)
            transition = self.transitions.get(key)
            
            if transition:
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
            else:
                # 상태 전이가 없더라도 미션 단계 업데이트 및 RUN 명령 전송
                print(f"[강제 처리] {truck_id}: FINISH_LOADING 이벤트이지만 상태 전이 없음, 강제 RUN 명령 전송")
                context.mission_phase = MissionPhase.TO_UNLOADING
                
                # RUN 명령 전송
                if self.command_sender:
                    self.command_sender.send(truck_id, "RUN", {})
            
            return True
        
        # ARRIVED 이벤트에서 BELT 도착 특별 처리
        if event == "ARRIVED" and "position" in payload and payload["position"] == "BELT":
            print(f"[특별 처리] {truck_id}: BELT 도착 이벤트 수신, 상태와 무관하게 STOP 명령 전송")
            # STOP 명령 전송
            if self.command_sender:
                self.command_sender.send(truck_id, "STOP")
        
        # ARRIVED_AT_* 명령 처리
        if event.startswith("ARRIVED_AT_"):
            position = event[11:]  # "ARRIVED_AT_" 접두사 제거
            context.position = position
            print(f"[위치 업데이트] {truck_id}: 위치 {position} (ARRIVED_AT 명령)")
            
            # 위치에 따른 미션 단계 업데이트
            self._update_mission_phase_by_position(context)
            
            # ARRIVED 이벤트로 변환하여 처리
            new_payload = dict(payload)
            new_payload["position"] = position
            return self.handle_event(truck_id, "ARRIVED", new_payload)
        
        # 위치 업데이트가 있는 경우
        if event == "ARRIVED" and "position" in payload:
            new_position = payload["position"]
            old_position = context.position
            context.position = new_position
            print(f"[위치 업데이트] {truck_id}: {old_position} → {new_position}")
            
            # 위치에 따른 미션 단계 업데이트
            self._update_mission_phase_by_position(context)
            
            # 체크포인트에 도착한 경우 게이트 제어가 필요
            if new_position.startswith("CHECKPOINT_"):
                print(f"[중요] {truck_id}: 체크포인트 {new_position}에 도착했습니다. 게이트 제어 필요!")

        # ASSIGN_MISSION 이벤트의 경우 상태에 관계없이 처리 가능하도록 함
        if event == "ASSIGN_MISSION" and current_state == TruckState.ASSIGNED:
            # 이미 트럭이 Assigned 상태이지만 대기 중이거나 새 미션을 할당받을 수 있는 상황
            if context.position == "STANDBY":
                print(f"[상태 무시 - 특수 처리] {truck_id}: {current_state}, {event}")
                self._assign_mission(context, payload)
                return True
        
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
            
            # 상태 전이가 없더라도 체크포인트 도착 이벤트는 게이트 제어 실행
            if event == "ARRIVED" and context.position.startswith("CHECKPOINT_"):
                print(f"[특수 처리] {truck_id}: 상태 전이 없지만 체크포인트 {context.position}에 도착하여 게이트 제어 실행")
                self._process_checkpoint_gate_control(context, context.position, context.direction)
                
            return False
    
    # -------------------------------------------------------------------------------   

    # 위치에 따른 미션 단계 업데이트
    def _update_mission_phase_by_position(self, context):
        position = context.position
        
        # 위치별 미션 단계 매핑
        position_to_phase = {
            "CHECKPOINT_A": MissionPhase.TO_LOADING if context.is_clockwise() else MissionPhase.RETURNING,
            "CHECKPOINT_B": MissionPhase.TO_LOADING if context.is_clockwise() else MissionPhase.RETURNING,
            "LOAD_A": MissionPhase.AT_LOADING,
            "LOAD_B": MissionPhase.AT_LOADING,
            "CHECKPOINT_C": MissionPhase.TO_UNLOADING if context.is_clockwise() else MissionPhase.RETURNING,
            "CHECKPOINT_D": MissionPhase.TO_UNLOADING if context.is_clockwise() else MissionPhase.RETURNING,
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
    
    # -------------------------------------------------------------------------------   

    # 미션 단계와 방향에 따른 다음 목표 위치 설정
    def _update_target_position(self, context):
        phase = context.mission_phase
        direction = context.direction
        current_position = context.position
        
        # 방향별 이동 경로 정의
        path_by_direction = {
            Direction.CLOCKWISE: {
                "STANDBY": "CHECKPOINT_A",
                "CHECKPOINT_A": "CHECKPOINT_B",
                "CHECKPOINT_B": None,  # LOAD_A나 LOAD_B로 가야 하므로 미션별로 결정되어야 함
                "LOAD_A": "CHECKPOINT_C",
                "LOAD_B": "CHECKPOINT_C",
                "CHECKPOINT_C": "CHECKPOINT_D",
                "CHECKPOINT_D": "BELT",
                "BELT": "STANDBY"              # 벨트에서 바로 STANDBY로 이동
            },
            Direction.COUNTERCLOCKWISE: {
                "STANDBY": "BELT",
                "BELT": "CHECKPOINT_D",
                "CHECKPOINT_D": "CHECKPOINT_C",
                "CHECKPOINT_C": None,  # LOAD_A나 LOAD_B로 가야 하므로 미션별로 결정되어야 함
                "LOAD_A": "CHECKPOINT_B",
                "LOAD_B": "CHECKPOINT_B",
                "CHECKPOINT_B": "CHECKPOINT_A",
                "CHECKPOINT_A": "STANDBY"
            }
        }
        
        # 현재 방향과 위치에 따른 다음 목표 위치 결정
        if direction in path_by_direction and current_position in path_by_direction[direction]:
            next_position = path_by_direction[direction][current_position]
            
            # CHECKPOINT_B나 CHECKPOINT_C에서는 특별히 처리 (미션별 적재 위치 결정)
            if next_position is None:
                if current_position == "CHECKPOINT_B" and direction == Direction.CLOCKWISE:
                    # 미션 정보에 따라 적재 위치 결정
                    loading_target = getattr(context, 'loading_target', "LOAD_A")
                    next_position = loading_target
                    print(f"[중요] {context.truck_id}: CHECKPOINT_B에서 미션별 적재 위치 → {loading_target} 설정")
                elif current_position == "CHECKPOINT_C" and direction == Direction.COUNTERCLOCKWISE:
                    # 반시계 방향일 때의 적재 위치 결정
                    loading_target = getattr(context, 'loading_target', "LOAD_A")
                    next_position = loading_target
                    print(f"[중요] {context.truck_id}: CHECKPOINT_C에서 미션별 적재 위치 → {loading_target} 설정")
            
            if next_position:  # None이 아닌 경우만 설정
                context.target_position = next_position
                print(f"[목표 위치 업데이트] {context.truck_id}: 현재 {current_position}, 다음 목표 → {next_position}")
                
        elif phase == MissionPhase.TO_LOADING:
            # 기본 목표 설정
            if context.position == "CHECKPOINT_A":
                context.target_position = "CHECKPOINT_B"  # GATE_A를 건너뛰고 직접 CHECKPOINT_B로
            elif context.position == "CHECKPOINT_B":
                # 미션 정보에 따라 적재 위치 결정 - 명시적으로 로딩 타겟 사용
                loading_target = getattr(context, 'loading_target', "LOAD_A")
                context.target_position = loading_target
                print(f"[적재 위치 설정] {context.truck_id}: 미션별 적재 위치 → {loading_target} (loading_target: {loading_target})")
                
                # 로딩 타겟과 현재 위치가 일치하지 않으면 경고
                if context.position in ["LOAD_A", "LOAD_B"] and context.position != loading_target:
                    print(f"[⚠️ 경고] {context.truck_id}: 현재 위치({context.position})와 설정된 적재 위치({loading_target})가 일치하지 않음")
                
        elif phase == MissionPhase.AT_LOADING:
            context.target_position = "CHECKPOINT_C"
        elif phase == MissionPhase.TO_UNLOADING:
            if context.position == "CHECKPOINT_C":
                context.target_position = "CHECKPOINT_D"  # GATE_B를 건너뛰고 직접 CHECKPOINT_D로
            elif context.position == "CHECKPOINT_D":
                context.target_position = "BELT"
        elif phase == MissionPhase.AT_UNLOADING:
            context.target_position = "STANDBY"  # 바로 대기장소로 이동
        elif phase == MissionPhase.RETURNING:
            context.target_position = "STANDBY"  # 어느 위치에서든 대기장소로
        else:
            context.target_position = None
        
        if context.target_position:
            print(f"[이동 경로] {context.truck_id}: {current_position} → {context.target_position} (방향: {direction.value}, 미션 단계: {phase})")
        
        # 디버그 정보: 현재 트럭의 컨텍스트 요약 출력
        if hasattr(context, 'loading_target'):
            print(f"[컨텍스트 요약] {context.truck_id}: 미션={context.mission_id}, 적재위치={context.loading_target}, 현재위치={context.position}, 목표={context.target_position}, 단계={context.mission_phase}")
        else:
            print(f"[컨텍스트 요약] {context.truck_id}: 미션={context.mission_id}, 적재위치=미설정, 현재위치={context.position}, 목표={context.target_position}, 단계={context.mission_phase}")
    
    # -------------------------------- 액션 메서드 --------------------------------

    # 미션 할당 처리
    def _assign_mission(self, context, payload):
        mission_id = payload.get("mission_id")
        source = payload.get("source", "LOAD_A")
        
        # 미션 ID가 없는 경우 - 할당할 미션이 없음
        if not mission_id:
            print(f"[미션 할당 실패] {context.truck_id}: 할당할 미션 ID가 없음")
            return False
        
        # 기존 상태 및 타겟 백업 (로깅용)
        old_mission_id = context.mission_id
        old_target = context.target_position
        
        # 새 미션 정보로 컨텍스트 업데이트
        context.mission_id = mission_id
        context.mission_phase = MissionPhase.TO_LOADING
        context.direction = Direction.CLOCKWISE
        context.target_position = "CHECKPOINT_A"  # 첫 목표는 CHECKPOINT_A
        
        # 소스에 따라 적재 위치 설정
        loading_target = source if source in ["LOAD_A", "LOAD_B"] else "LOAD_A"
        context.loading_target = loading_target  # 적재 위치 저장
        
        print(f"[미션 할당] {context.truck_id}: 미션 {mission_id}, 출발지 {source}, 적재 위치 {loading_target}, 방향 {context.direction.value}")
        if old_mission_id or old_target:
            print(f"[상태 변경] {context.truck_id}: 이전 미션 {old_mission_id} → 새 미션 {mission_id}, 타겟 {old_target} → {context.target_position}")
        
        # 트럭에 이동 명령 전송
        if self.command_sender:
            # 1. MISSION_ASSIGNED 명령 먼저 전송 - source만 포함
            self.command_sender.send(context.truck_id, "MISSION_ASSIGNED", {
                "source": source
            })
            
            # 1초 대기 (트럭이 미션 정보를 처리할 시간 제공)
            time.sleep(1.0)
            
            # 2. RUN 명령 전송 - 타겟 정보 없이 단순 RUN만 전송
            # 트럭 시뮬레이터가 자체적으로 다음 위치를 결정
            self.command_sender.send(context.truck_id, "RUN", {})
            
        return True
    
    # -------------------------------------------------------------------------------   

    # 이동 시작 처리
    def _start_moving(self, context, payload):
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {
                "target": context.target_position
            })
    
    # -------------------------------------------------------------------------------   

    # 도착 처리
    def _handle_arrival(self, context, payload):
        position = context.position
        direction = context.direction
        
        print(f"[도착 처리] {context.truck_id}: 위치 {position}, 방향 {direction.value}")
        
        # 방향 전환점에 도착한 경우 방향 업데이트
        if position in self.direction_transition_points:
            new_direction = self.direction_transition_points[position]
            if new_direction != direction:
                old_direction = context.update_direction(new_direction)
                print(f"[방향 전환] {context.truck_id}: {old_direction.value} → {new_direction.value}")
                direction = new_direction
        
        # 체크포인트에 도착한 경우 게이트 제어
        if position.startswith("CHECKPOINT_"):
            # 게이트 제어 로직 실행
            self._process_checkpoint_gate_control(context, position, direction)
                
        # 작업 위치에 도착한 경우 처리
        elif position in ["LOAD_A", "LOAD_B"]:
            # 미션에 설정된 loading_target과 현재 위치 비교
            loading_target = getattr(context, 'loading_target', None)
            
            if loading_target and position != loading_target:
                # 미션에 설정된 적재 위치와 실제 도착한 위치가 다른 경우
                print(f"[⚠️ 경고] {context.truck_id}: 잘못된 적재 위치에 도착! 현재={position}, 설정된 적재위치={loading_target}")
                
                # 올바른 위치로 이동 명령
                if self.command_sender:
                    print(f"[🔄 자동 이동] {context.truck_id}: 잘못된 위치({position})에서 올바른 적재 위치({loading_target})로 이동")
                    # 이동 명령 전송
                    self.command_sender.send(context.truck_id, "RUN", {
                        "target": loading_target
                    })
                    return  # 이 위치에서의 다른 처리는 중단
            
            # 정상적인 경우 - 올바른 적재 위치에 도착했거나 loading_target이 설정되지 않은 경우
            print(f"[✅ 적재 위치 도착] {context.truck_id}: {position}에 도착")
            if self.command_sender:
                self.command_sender.send(context.truck_id, "STOP")
        
        # 하차 위치(BELT)에 도착한 경우
        elif position == "BELT":
            print(f"[✅ 하차 위치 도착] {context.truck_id}: {position}에 도착")
            if self.command_sender:
                self.command_sender.send(context.truck_id, "STOP")
                
        # 대기장소 도착 - 미션 완료 처리
        elif position == "STANDBY":
            # 미션 완료 처리
            if context.mission_phase == MissionPhase.RETURNING and context.mission_id:
                print(f"[미션 완료] {context.truck_id}: 미션 {context.mission_id} 완료 및 대기 상태로 전환")
                
                # 미션 매니저로 미션 완료 처리
                if self.mission_manager and context.mission_id:
                    # 현재 미션 ID 저장 (완료 전에)
                    completed_mission_id = context.mission_id
                    
                    # 미션 상태 업데이트
                    context.mission_phase = MissionPhase.COMPLETED
                    context.mission_id = None
                    
                    # 미션 매니저에 완료 알림
                    self.mission_manager.complete_mission(completed_mission_id)
                    
                    # 잠시 대기 (0.5초) - 미션 완료 처리를 위한 여유
                    time.sleep(0.5)
                    
                    # 새 미션 할당 시도
                    print(f"[미션 할당 시도] {context.truck_id}에 새 미션 할당 시도")
                    mission_assigned = self.handle_event(context.truck_id, "ASSIGN_MISSION", {})
                    
                    # 미션 할당 실패 시 상태 초기화 및 배터리 확인
                    if not mission_assigned:
                        print(f"[미션 할당 실패] {context.truck_id}에 할당할 미션이 없음 - 상태 초기화")
                        context.state = TruckState.IDLE
                        context.mission_phase = MissionPhase.NONE
                        context.target_position = None
                        
                        # 배터리 상태 확인 후 필요시 충전 시작
                        if self._needs_charging(context, {}):
                            print(f"[배터리 확인] {context.truck_id}: 배터리 부족 ({context.battery_level}%) - 충전 시작")
                            self._start_charging(context, {})
                        else:
                            print(f"[배터리 확인] {context.truck_id}: 배터리 상태 양호 ({context.battery_level}%) - 대기 상태 유지")
    
    # -------------------------------------------------------------------------------   

    # 체크포인트에서의 게이트 제어 처리
    def _process_checkpoint_gate_control(self, context, checkpoint, direction):
        """체크포인트에서의 게이트 제어 처리"""
        print(f"[체크포인트 도착] {context.truck_id}: 체크포인트 {checkpoint}, 방향 {direction.value}")
        
        # 각 방향별 체크포인트 도착 시 게이트 처리 정의
        checkpoint_gate_actions = {
            "CHECKPOINT_A": {
                Direction.CLOCKWISE: {"open": "GATE_A", "close": None},        # 시계방향: GATE_A 열기
                Direction.COUNTERCLOCKWISE: {"open": None, "close": "GATE_A"}  # 반시계방향: GATE_A 닫기
            },
            "CHECKPOINT_B": {
                Direction.CLOCKWISE: {"open": None, "close": "GATE_A"},        # 시계방향: GATE_A 닫기
                Direction.COUNTERCLOCKWISE: {"open": "GATE_A", "close": None}  # 반시계방향: GATE_A 열기
            },
            "CHECKPOINT_C": {
                Direction.CLOCKWISE: {"open": "GATE_B", "close": None},        # 시계방향: GATE_B 열기
                Direction.COUNTERCLOCKWISE: {"open": None, "close": "GATE_B"}  # 반시계방향: GATE_B 닫기
            },
            "CHECKPOINT_D": {
                Direction.CLOCKWISE: {"open": None, "close": "GATE_B"},        # 시계방향: GATE_B 닫기
                Direction.COUNTERCLOCKWISE: {"open": "GATE_B", "close": None}  # 반시계방향: GATE_B 열기
            }
        }
        
        # 게이트 액션이 필요한지 확인
        has_gate_action = False
        
        # 특수 처리: CHECKPOINT_B에서 직접 GATE_A 닫기
        if checkpoint == "CHECKPOINT_B" and direction == Direction.CLOCKWISE:
            print(f"[🔒 중요 게이트 제어] CHECKPOINT_B에서 GATE_A 닫기 명령 강제 실행")
            close_result = self._close_gate_and_log("GATE_A", context.truck_id)
            print(f"[게이트 닫기 결과] GATE_A: {'성공' if close_result else '실패'}")
            has_gate_action = True
            
            # 2초 대기하여 게이트 닫힘 동작 완료 확인
            time.sleep(2)
            
            # 게이트 닫힌 후에 이동 명령 전송
            if self.command_sender:
                print(f"[🔄 게이트 제어 후 이동] {context.truck_id}: GATE_A 닫은 후 이동")
                self.command_sender.send(context.truck_id, "RUN", {})
                
            return
            
        # 특수 처리: CHECKPOINT_C에서 직접 GATE_B 열기
        elif checkpoint == "CHECKPOINT_C" and direction == Direction.CLOCKWISE:
            print(f"[🔓 중요 게이트 제어] CHECKPOINT_C에서 GATE_B 열기 명령 강제 실행")
            open_result = self._open_gate_and_log("GATE_B", context.truck_id)
            print(f"[게이트 열기 결과] GATE_B: {'성공' if open_result else '실패'}")
            has_gate_action = True
            
            # 2초 대기하여 게이트 열림 동작 완료 확인
            time.sleep(2)
            
            # 게이트 열림 후에 이동 명령 전송 안 함 (게이트 열림 이벤트 처리에서 자동으로 이동)
            # 트럭은 이후 GATE_OPENED 메시지를 수신하면 자동으로 이동
                
            return
        
        # 해당 체크포인트에 대한 액션 가져오기
        if checkpoint in checkpoint_gate_actions:
            # 디버그 로그 추가
            print(f"[체크포인트 액션 결정] {checkpoint}, 방향: {direction.value}, 액션 정의: {checkpoint_gate_actions[checkpoint].get(direction, {})}")
            
            actions = checkpoint_gate_actions[checkpoint].get(direction, {})
            
            # 게이트 열기 액션
            if "open" in actions and actions["open"]:
                gate_id = actions["open"]
                print(f"[게이트 제어] 열기: {gate_id}, 체크포인트: {checkpoint}, 방향: {direction.value}")
                
                # CHECKPOINT_C에서 GATE_B 열기 특별 처리 추가
                if checkpoint == "CHECKPOINT_C" and gate_id == "GATE_B" and direction == Direction.CLOCKWISE:
                    print(f"[중요 게이트 제어] CHECKPOINT_C에서 GATE_B 열기 명령 실행")
                
                open_result = self._open_gate_and_log(gate_id, context.truck_id)
                print(f"[게이트 열기 결과] {gate_id}: {'성공' if open_result else '실패'}")
                has_gate_action = True
            
            # 게이트 닫기 액션
            if "close" in actions and actions["close"]:
                gate_id = actions["close"]
                print(f"[게이트 제어] 닫기: {gate_id}, 체크포인트: {checkpoint}, 방향: {direction.value}")
                
                # CHECKPOINT_B에서 GATE_A 닫기 특별 처리
                if checkpoint == "CHECKPOINT_B" and gate_id == "GATE_A" and direction == Direction.CLOCKWISE:
                    print(f"[중요 게이트 제어] CHECKPOINT_B에서 GATE_A 닫기 명령 실행")
                
                # CHECKPOINT_D에서 GATE_B 닫기 특별 처리 추가
                if checkpoint == "CHECKPOINT_D" and gate_id == "GATE_B" and direction == Direction.CLOCKWISE:
                    print(f"[중요 게이트 제어] CHECKPOINT_D에서 GATE_B 닫기 명령 실행")
                
                close_result = self._close_gate_and_log(gate_id, context.truck_id)
                print(f"[게이트 닫기 결과] {gate_id}: {'성공' if close_result else '실패'}")
                has_gate_action = True
            
            # 게이트 액션이 없는 경우 바로 다음 위치로 이동 명령
            if not has_gate_action:
                print(f"[게이트 제어 없음] {context.truck_id}: 체크포인트 {checkpoint}에서 게이트 제어가 필요 없습니다.")
                # 바로 RUN 명령 전송
                if self.command_sender:
                    print(f"[자동 이동] {context.truck_id}: 게이트 제어 없이 바로 다음 위치로 이동")
                    self.command_sender.send(context.truck_id, "RUN", {})
        else:
            print(f"[알 수 없는 체크포인트] {checkpoint}에 대한 게이트 제어 정의가 없습니다.")
        
        # 위치에 따른 자동 명령 (체크포인트지만 자동 RUN 명령을 보내지 않는 특수 경우)
        if not has_gate_action and checkpoint not in ["CHECKPOINT_A", "CHECKPOINT_C"]:  # CHECKPOINT_A, CHECKPOINT_C는 게이트 열기 후 이동
            # 다음 목표로 자동 이동 (체크포인트에서 경로 계속)
            if self.command_sender:
                print(f"[자동 이동] {context.truck_id}: {context.position}에서 다음 위치로 이동")
                # 단순 RUN 명령 - 트럭이 자체적으로 다음 위치 결정
                self.command_sender.send(context.truck_id, "RUN", {})
    
    # -------------------------------------------------------------------------------   

    # 게이트 열림 처리
    def _handle_gate_opened(self, context, payload):
        """게이트 열림 처리"""
        # 다음 위치로 이동 명령
        if self.command_sender:
            print(f"[게이트 열림 후 이동] {context.truck_id}: 게이트가 열렸으므로 자동으로 이동합니다.")
            
            # 단순 RUN 명령 - 트럭이 자체적으로 다음 위치 결정
            self.command_sender.send(context.truck_id, "RUN", {})
    
    # -------------------------------------------------------------------------------   

    # 적재 작업 시작 처리
    def _start_loading(self, context, payload):
        """적재 작업 시작 처리"""
        print(f"[적재 시작] {context.truck_id}: 위치 {context.position}에서 적재 작업 시작")
        # 필요한 경우 추가 액션 수행

    # -------------------------------------------------------------------------------   

    # 적재 완료 및 이동 처리
    def _finish_loading_and_move(self, context, payload):
        """적재 완료 및 이동 처리"""
        print(f"[적재 완료] {context.truck_id}: 적재 작업 완료, 다음 위치로 이동")
        
        # 방향 유지 (시계방향 - 정상 흐름)
        # 이미 Direction.CLOCKWISE로 설정되어 있으므로 변경 필요 없음
        
        # 다음 단계 업데이트
        context.mission_phase = MissionPhase.TO_UNLOADING
        
        # 이동 명령 전송 - 트럭이 자체적으로 다음 위치 결정
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {})
    
    # -------------------------------------------------------------------------------   

    # 하차 작업 시작 처리
    def _start_unloading(self, context, payload):
        """하차 작업 시작 처리"""
        print(f"[하차 시작] {context.truck_id}: 위치 {context.position}에서 하차 작업 시작")
        
        # 벨트 작동 명령 전송
        if self.belt_controller:
            print(f"[벨트 작동] {context.truck_id} → 벨트에 RUN 명령 전송")
            self.belt_controller.send_command("BELT", "RUN")
    
    # -------------------------------------------------------------------------------   

    # 하차 완료 및 이동 처리
    def _finish_unloading_and_move(self, context, payload):
        """하차 완료 및 이동 처리"""
        print(f"[하차 완료] {context.truck_id}: 하차 작업 완료, 바로 대기장소로 복귀")
        
        # 방향 유지 (시계방향 - 정상 흐름)
        # 이미 Direction.CLOCKWISE로 설정되어 있으므로 변경 필요 없음
        
        # 다음 단계 업데이트
        context.mission_phase = MissionPhase.RETURNING
        
        # 이동 명령 전송 - 트럭이 자체적으로 다음 위치 결정
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {})
            
        # 벨트 중지 명령
        if self.belt_controller:
            print(f"[벨트 중지] {context.truck_id} → 벨트에 STOP 명령 전송")
            self.belt_controller.send_command("BELT", "STOP")
    
    # -------------------------------------------------------------------------------   

    # 이동 재개 처리
    def _resume_moving(self, context, payload):
        """이동 재개 처리"""
        if self.command_sender:
            self.command_sender.send(context.truck_id, "RUN", {})
    
    # -------------------------------------------------------------------------------   

    # 충전 시작 처리
    def _start_charging(self, context, payload):
        """충전 시작 처리"""
        context.is_charging = True
        print(f"[충전 시작] {context.truck_id}: 배터리 레벨 {context.battery_level}%")
        
        if self.command_sender:
            self.command_sender.send(context.truck_id, "START_CHARGING")
    
    # -------------------------------------------------------------------------------   

    # 충전 완료 처리
    def _finish_charging(self, context, payload):
        context.is_charging = False
        print(f"[충전 완료] {context.truck_id}: 배터리 레벨 {context.battery_level}%")
        
        if self.command_sender:
            self.command_sender.send(context.truck_id, "CHARGING_COMPLETED")
            
        # 완충 후 미션 할당 시도
        self.handle_event(context.truck_id, "ASSIGN_MISSION", {})
    
    # -------------------------------------------------------------------------------   

    # 비상 상황 처리
    def _handle_emergency(self, context, payload):
        print(f"[⚠️ 비상 상황] {context.truck_id}: 비상 정지")
        
        # 트럭 정지 명령
        if self.command_sender:
            self.command_sender.send(context.truck_id, "STOP")
        
        # 벨트 정지 명령
        if self.belt_controller:
            self.belt_controller.send_command("BELT", "EMRSTOP")
    
    # -------------------------------------------------------------------------------   

    # 비상 상황 해제 처리
    def _reset_from_emergency(self, context, payload):
        print(f"[🔄 비상 해제] {context.truck_id}: 기본 상태로 복귀")
        
        # 미션 취소 처리
        if context.mission_id and self.mission_manager:
            self.mission_manager.cancel_mission(context.mission_id)
            context.mission_id = None
            context.mission_phase = MissionPhase.NONE

    # -------------------------------- 조건 메서드 --------------------------------
    
    def _can_accept_mission(self, context, payload):
        """미션 수락 가능 여부 확인"""
        # STANDBY 위치에 있는 경우, 이전 미션이 있어도 새 미션 할당 허용
        if context.position == "STANDBY":
            # 충전 중이거나 비상 상태가 아닌지만 확인
            if context.is_charging:
                print(f"[미션 거부] {context.truck_id}: 충전 중")
                return False
                
            # 비상 상태인 경우 수락 불가
            if context.state == TruckState.EMERGENCY:
                print(f"[미션 거부] {context.truck_id}: 비상 상태")
                return False
                
            # 기존 미션이 있으면 로그 남기고 초기화
            if context.mission_id is not None:
                print(f"[미션 초기화] {context.truck_id}: 이전 미션 {context.mission_id}를 새 미션으로 대체합니다")
                # 이전 미션 정보 초기화
                context.mission_id = None
                context.mission_phase = MissionPhase.NONE
            
            return True
                
        # 일반적인 경우 - 기존 로직 유지
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
        return context.position in ["LOAD_A", "LOAD_B"]
    
    def _is_at_unloading_area(self, context, payload):
        return context.position == "BELT"
    
    def _needs_charging(self, context, payload):
        return context.battery_level <= self.BATTERY_THRESHOLD
    
    def _is_fully_charged(self, context, payload):
        return context.battery_level >= self.BATTERY_FULL
    
    # -------------------------------- 게이트 제어 메서드 --------------------------------
    
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
            self.command_sender.send(truck_id, "GATE_OPENED", {"gate_id": gate_id})
        else:
            print(f"[⚠️ 경고] command_sender가 없어 GATE_OPENED 메시지를 전송할 수 없습니다.")
            
        return success
    
    def _close_gate_and_log(self, gate_id, truck_id):
        success = False
        
        print(f"[🔒 게이트 닫기 시도] {gate_id} ← by {truck_id}")
        
        if self.gate_controller:
            success = self.gate_controller.close_gate(gate_id)
            if success:
                print(f"[🔒 GATE CLOSE] {gate_id} ← by {truck_id}")
        else:
            # 테스트 모드에서는 성공으로 처리
            print(f"[🔒 GATE CLOSE 시뮬레이션] {gate_id} ← by {truck_id} (게이트 컨트롤러 없음)")
            success = True
                
        # 트럭에 게이트 닫힘 알림 전송 비활성화 (일시적 조치)
        print(f"[⚠️ 알림 비활성화] {truck_id}에게 GATE_CLOSED 메시지 전송이 비활성화되었습니다")
        # if self.command_sender:
        #     print(f"[📤 게이트 닫힘 알림] {truck_id}에게 GATE_CLOSED 메시지 전송 (gate_id: {gate_id})")
        #     self.command_sender.send(truck_id, "GATE_CLOSED", {"gate_id": gate_id})
        # else:
        #     print(f"[⚠️ 경고] command_sender가 없어 GATE_CLOSED 메시지를 전송할 수 없습니다.")
            
        # 게이트 닫힘 후 자동으로 트럭에게 RUN 명령 전송
        if success and self.command_sender:
            print(f"[🔄 게이트 닫힘 후 자동 이동] {truck_id}: 게이트가 닫혔으므로 자동으로 이동 명령 전송")
            # 짧은 대기 후 실행 (게이트가 완전히 닫힌 후)
            time.sleep(1.0)
            self.command_sender.send(truck_id, "RUN", {})
            
        return success
    
    # -------------------------------- 위치 관리 메서드 --------------------------------
    
    def handle_position_update(self, truck_id, new_position, payload=None):
        if payload is None:
            payload = {}
            
        context = self._get_or_create_context(truck_id)
        old_position = context.position
        
        # 위치 업데이트
        context.position = new_position
        print(f"[위치 변경] {truck_id}: {old_position} → {new_position}")
        
        # BELT 위치에 도착한 경우 항상 STOP 명령 전송
        if new_position == "BELT":
            print(f"[특별 처리] {truck_id}: BELT 위치 도착 감지, 항상 STOP 명령 전송")
            if self.command_sender:
                self.command_sender.send(truck_id, "STOP")
        
        # 위치 기반 이벤트 생성
        payload["position"] = new_position
        self.handle_event(truck_id, "ARRIVED", payload)
        
        # 위치와 상태의 일관성 검증
        self._validate_position_state_consistency(context)
        
        return True
    
    def _validate_position_state_consistency(self, context):
        position = context.position
        state = context.state
        
        # 특정 상태에서 예상되는 위치 정의
        state_to_expected_positions = {
            TruckState.LOADING: ["LOAD_A", "LOAD_B"],
            TruckState.UNLOADING: ["BELT"],
            TruckState.WAITING: ["CHECKPOINT_A", "CHECKPOINT_C", "BELT", "LOAD_A", "LOAD_B", "CHECKPOINT_B", "CHECKPOINT_D"]
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

    # -------------------------------------------------------------------------------   

    def _add_assigned_state_transitions(self):
        # ASSIGNED 상태에서 위치 도착 시 WAITING으로 변경
        self.transitions[(TruckState.ASSIGNED, "ARRIVED")] = {
            "next_state": TruckState.WAITING,
            "action": self._handle_arrival,
            "condition": None
        }
        
        # ASSIGNED 상태에서 ACK_GATE_OPENED 이벤트 시 MOVING으로 변경
        self.transitions[(TruckState.ASSIGNED, "ACK_GATE_OPENED")] = {
            "next_state": TruckState.MOVING, 
            "action": self._handle_gate_opened,
            "condition": None
        }
        
        # ASSIGNED 상태에서도 로딩/언로딩 시작 가능
        self.transitions[(TruckState.ASSIGNED, "START_LOADING")] = {
            "next_state": TruckState.LOADING,
            "action": self._start_loading,
            "condition": self._is_at_loading_area
        }
        
        self.transitions[(TruckState.ASSIGNED, "START_UNLOADING")] = {
            "next_state": TruckState.UNLOADING,
            "action": self._start_unloading,
            "condition": self._is_at_unloading_area
        }
        
        # ASSIGNED 상태에서 로딩/언로딩 완료 처리
        self.transitions[(TruckState.ASSIGNED, "FINISH_LOADING")] = {
            "next_state": TruckState.MOVING,
            "action": self._finish_loading_and_move,
            "condition": None
        }
        
        # WAITING 상태에서도 FINISH_LOADING 이벤트 처리
        self.transitions[(TruckState.WAITING, "FINISH_LOADING")] = {
            "next_state": TruckState.MOVING,
            "action": self._finish_loading_and_move,
            "condition": None
        }
        
        self.transitions[(TruckState.ASSIGNED, "FINISH_UNLOADING")] = {
            "next_state": TruckState.MOVING,
            "action": self._finish_unloading_and_move,
            "condition": None
        }

        # 미션 취소 처리 전이 추가
        self.transitions[(TruckState.ASSIGNED, "CANCEL_MISSION")] = {
            "next_state": TruckState.IDLE,
            "action": self._handle_mission_cancellation,
            "condition": None
        }
        
        # WAITING 상태에서도 미션 취소 가능
        self.transitions[(TruckState.WAITING, "CANCEL_MISSION")] = {
            "next_state": TruckState.IDLE,
            "action": self._handle_mission_cancellation,
            "condition": None
        }
        
        # MOVING 상태에서도 미션 취소 가능 (로딩 시작 전에만)
        self.transitions[(TruckState.MOVING, "CANCEL_MISSION")] = {
            "next_state": TruckState.IDLE,
            "action": self._handle_mission_cancellation,
            "condition": self._can_cancel_mission
        }

    def _extend_finish_unloading_action(self):
        """하역 완료 액션 확장"""
        # 하역 완료 액션에 미션 완료 로직 추가
        original_action = self._finish_unloading_and_move
        
        def extended_action(context, payload):
            # 원래 액션 호출
            original_action(context, payload)
            
            # 방향을 시계 방향으로 유지
            context.direction = Direction.CLOCKWISE
            
            # 추가 로직 (필요시)
            print(f"[언로딩 완료 확장] {context.truck_id}: 방향을 {context.direction.value}로 설정")
            
        # 액션 교체
        self.transitions[(TruckState.UNLOADING, "FINISH_UNLOADING")]["action"] = extended_action
        
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
        # 로딩이 시작되기 전에만 취소 가능
        return (context.mission_phase in [MissionPhase.TO_LOADING, MissionPhase.NONE] and
                context.state != TruckState.LOADING) 