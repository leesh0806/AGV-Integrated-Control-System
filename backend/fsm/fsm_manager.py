# backend/fsm/fsm_manager.py

from .state_enum import TruckState
from ..mission.status import MissionStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tcpio.truck_commander import TruckCommandSender

from datetime import datetime
from ..battery.manager import BatteryManager

class TruckFSMManager:
    def __init__(self, gate_controller, mission_manager, belt_controller=None, battery_manager=None):
        self.gate_controller = gate_controller
        self.mission_manager = mission_manager
        self.belt_controller = belt_controller
        self.battery_manager = battery_manager
        self.states = {}
        self.command_sender = None
        self.BATTERY_THRESHOLD = 30  # 배터리 임계값 설정
        self.BATTERY_FULL = 100  # 배터리 만충전 기준

    # -------------------------------------------------------------------

    # 명령 전송 설정
    def set_commander(self, commander: 'TruckCommandSender'):
        self.command_sender = commander

    # 트럭 상태 조회
    def get_state(self, truck_id):
        return self.states.get(truck_id, TruckState.IDLE)

    # 트럭 상태 설정
    def set_state(self, truck_id, new_state):
        prev = self.get_state(truck_id)
        self.states[truck_id] = new_state
        print(f"[FSM] {truck_id}: {prev.name} → {new_state.name}")

    # 트럭 주행 명령
    def send_run(self, truck_id):
        if self.command_sender:
            self.command_sender.send(truck_id, "RUN")

    # 트럭 정지 명령
    def send_stop(self, truck_id):
        if self.command_sender:
            self.command_sender.send(truck_id, "STOP")

    # -------------------------------------------------------------------

    # 게이트 열림 로깅 및 명령 전송
    def _open_gate_and_log(self, gate_id: str, truck_id: str):
        success = self.gate_controller.open_gate(gate_id)
        if success:
            print(f"[🔓 GATE OPEN] {gate_id} ← by {truck_id}")
            if self.command_sender:
                self.command_sender.send(truck_id, "GATE_OPENED", {"gate_id": gate_id})
        return success

    # 게이트 닫기 로깅 및 명령 전송
    def _close_gate_and_log(self, gate_id: str, truck_id: str):
        success = self.gate_controller.close_gate(gate_id)
        if success:
            print(f"[🔒 GATE CLOSE] {gate_id} ← by {truck_id}")
            if self.command_sender:
                self.command_sender.send(truck_id, "GATE_CLOSED", {"gate_id": gate_id})
        return success

    # -------------------------------------------------------------------

    # 트리거 처리
    def handle_trigger(self, truck_id, cmd, payload):
        try:
            state = self.get_state(truck_id)
            print(f"[FSM] 트리거: {truck_id}, 상태={state.name}, 트리거={cmd}")

            # IDLE 상태에서 미션 할당
            if (state == TruckState.IDLE or state == TruckState.WAIT_NEXT_MISSION) and cmd == "ASSIGN_MISSION":
                print("[DEBUG] ASSIGN_MISSION: DB에서 미션 새로 불러옴")
                self.mission_manager.load_from_db()
                
                # 다음 미션 존재 여부 확인
                has_next_mission = len(self.mission_manager.waiting_queue) > 0
                print(f"[DEBUG] 대기 중인 미션 수: {len(self.mission_manager.waiting_queue)}")
                
                # 배터리 레벨 확인
                if not payload or 'battery_level' not in payload:
                    # battery_manager에서 배터리 정보 확인
                    if self.battery_manager:
                        battery = self.battery_manager.get_battery(truck_id)
                        battery_level = battery.level
                        print(f"[🔋 배터리 체크] {truck_id}의 배터리: {battery_level}% (battery_manager에서 조회)")
                    else:
                        print(f"[⚠️ 경고] {truck_id}의 배터리 정보가 없음 - 충전 필요")
                        self.set_state(truck_id, TruckState.CHARGING)
                        if self.command_sender:
                            self.command_sender.send(truck_id, "START_CHARGING", {})
                        return
                else:
                    battery_level = payload['battery_level']
                    print(f"[🔋 배터리 체크] {truck_id}의 배터리: {battery_level}% (payload에서 조회)")
                
                if has_next_mission:
                    next_mission = self.mission_manager.waiting_queue[0]
                    print(f"[DEBUG] 다음 미션 정보: ID={next_mission.mission_id}, 상태={next_mission.status.name}")
                    
                    if battery_level <= self.BATTERY_THRESHOLD:  # 배터리가 임계값 이하면
                        print(f"[🔋 배터리 부족] {truck_id}의 배터리: {battery_level}%")
                        self.set_state(truck_id, TruckState.CHARGING)
                        if self.command_sender:
                            self.command_sender.send(truck_id, "START_CHARGING", {})
                        if self.battery_manager:
                            self.battery_manager.update_battery(truck_id, battery_level, True)
                        return
                    
                    # 배터리가 충분하면 미션 진행
                    mission = self.mission_manager.assign_next_to_truck(truck_id)
                    if mission:
                        self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_LOAD)
                        print(f"[지시] {truck_id} → CHECKPOINT_A로 이동")
                        self.send_run(truck_id)
                        self.command_sender.send(truck_id, "MISSION_ASSIGNED", {
                            "source": mission.source
                        })
                        return
                else:
                    # 미션이 없을 때는 배터리 상태에 따라 처리
                    print(f"[🔋 미션 없음] {truck_id}의 배터리: {battery_level}%")
                    
                    # 먼저 NO_MISSION 메시지를 항상 전송
                    if self.command_sender:
                        if battery_level < self.BATTERY_FULL:
                            self.command_sender.send(truck_id, "NO_MISSION", {"reason": "BATTERY_LOW"})
                        else:
                            self.command_sender.send(truck_id, "NO_MISSION", {"reason": "NO_MISSIONS_AVAILABLE"})
                    
                    # 그 다음 배터리 상태에 따라 충전 명령 보내기
                    if battery_level < self.BATTERY_FULL:  # 배터리가 100%가 아닐 때만 충전
                        print(f"[🔋 충전 필요] {truck_id}의 배터리: {battery_level}% - 충전 상태로 전환")
                        self.set_state(truck_id, TruckState.CHARGING)
                        if self.command_sender:
                            self.command_sender.send(truck_id, "START_CHARGING", {})
                        if self.battery_manager:
                            self.battery_manager.update_battery(truck_id, battery_level, True)
                    else:
                        print(f"[🔋 충전 불필요] {truck_id}의 배터리: {battery_level}% - 대기 상태 유지")
                        self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)
                return

            # 이미 미션 진행 중일 때 ASSIGN_MISSION 요청이 오면 현재 상태 응답
            elif cmd == "ASSIGN_MISSION":
                current_state = self.get_state(truck_id)
                print(f"[ℹ️ 중복 요청] {truck_id}의 현재 상태: {current_state.name}")
                
                if current_state == TruckState.MOVE_TO_GATE_FOR_LOAD:
                    # 이미 미션이 할당된 상태면 현재 미션 정보 재전송
                    mission = self.mission_manager.get_mission_by_truck(truck_id)
                    if mission:
                        self.command_sender.send(truck_id, "MISSION_ASSIGNED", {
                            "source": mission.source
                        })
                        return
                elif current_state == TruckState.CHARGING:
                    # 충전 중이면 NO_MISSION 응답
                    self.command_sender.send(truck_id, "NO_MISSION", {"reason": "CHARGING"})
                    return
                elif current_state == TruckState.EMERGENCY_STOP:
                    # 비상 정지 상태면 NO_MISSION 응답
                    self.command_sender.send(truck_id, "NO_MISSION", {"reason": "EMERGENCY"})
                    return
                else:
                    # 기타 상태면 현재 상태 정보만 전송
                    self.command_sender.send(truck_id, "CURRENT_STATE", {
                        "state": current_state.name
                    })
                    return
            
            # -------------------------------------------------------------------

            # 충전 중일 때 미션 할당 요청이 오면 NO_MISSION 응답
            elif state == TruckState.CHARGING and cmd == "ASSIGN_MISSION":
                print("[DEBUG] ASSIGN_MISSION: DB에서 미션 새로 불러옴")
                self.mission_manager.load_from_db()
                
                # 다음 미션 존재 여부 확인
                has_next_mission = len(self.mission_manager.waiting_queue) > 0
                print(f"[DEBUG] 대기 중인 미션 수: {len(self.mission_manager.waiting_queue)}")
                
                if has_next_mission:
                    next_mission = self.mission_manager.waiting_queue[0]
                    print(f"[DEBUG] 다음 미션 정보: ID={next_mission.mission_id}, 상태={next_mission.status.name}")
                    
                    # 배터리 레벨 확인
                if self.command_sender:
                    self.command_sender.send(truck_id, "NO_MISSION", {"reason": "CHARGING"})
                return
            
            # -------------------------------------------------------------------

            # 대기장 도착
            elif state == TruckState.MOVE_TO_STANDBY and cmd == "ARRIVED_AT_STANDBY":
                self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)
                self.handle_trigger(truck_id, "ASSIGN_MISSION", {})
                return
            
            # -------------------------------------------------------------------

            # 충전 완료
            elif state == TruckState.CHARGING and cmd == "FINISH_CHARGING":
                if not self.battery_manager.get_battery(truck_id).is_fully_charged:
                    print(f"[🔋 충전 계속] {truck_id}의 배터리: {self.battery_manager.get_battery(truck_id).level}%")
                    return
                    
                self.set_state(truck_id, TruckState.IDLE)
                if self.command_sender:
                    self.command_sender.send(truck_id, "CHARGING_COMPLETED", {})
                if self.battery_manager:
                    self.battery_manager.update_battery(truck_id, self.battery_manager.get_battery(truck_id).level, False)
                # 충전 완료 후 미션 할당 시도
                self.handle_trigger(truck_id, "ASSIGN_MISSION", {})
                return
            
            # -------------------------------------------------------------------

            # 게이트 A에 도착
            elif state == TruckState.MOVE_TO_GATE_FOR_LOAD and cmd == "ARRIVED_AT_CHECKPOINT_A":
                self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_LOAD)
                self.send_stop(truck_id)  # 트럭 정지
                gate_id = payload.get("gate_id", "GATE_A")
                self._open_gate_and_log(gate_id, truck_id)
                return
            
            # -------------------------------------------------------------------

            # 게이트 열림 확인
            elif state == TruckState.WAIT_GATE_OPEN_FOR_LOAD and cmd == "ACK_GATE_OPENED":
                self.set_state(truck_id, TruckState.MOVE_TO_LOAD)
                self.send_run(truck_id)
                return
            
            # -------------------------------------------------------------------

            # CHECKPOINT_B 도착 (GATE_A 닫기)
            elif state == TruckState.MOVE_TO_LOAD and cmd == "ARRIVED_AT_CHECKPOINT_B":
                # self.send_stop(truck_id)  # 트럭 정지
                gate_id = payload.get("gate_id", "GATE_A")
                self._close_gate_and_log(gate_id, truck_id)
                return
            
            # -------------------------------------------------------------------

            # 적재장 도착
            elif state == TruckState.MOVE_TO_LOAD and (cmd == "ARRIVED_AT_LOAD_A" or cmd == "ARRIVED_AT_LOAD_B"):
                self.set_state(truck_id, TruckState.WAIT_LOAD)
                self.send_stop(truck_id)  # 트럭 정지
                return
            
            # -------------------------------------------------------------------

            # 적재 시작
            elif state == TruckState.WAIT_LOAD and cmd == "START_LOADING":
                self.set_state(truck_id, TruckState.LOADING)
                return
            
            # -------------------------------------------------------------------

            # 적재 완료
            elif state == TruckState.LOADING and cmd == "FINISH_LOADING":
                self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_UNLOAD)
                print(f"[지시] {truck_id} → CHECKPOINT_C로 이동")
                self.send_run(truck_id)
                return

            # 게이트 B에 도착
            elif state == TruckState.MOVE_TO_GATE_FOR_UNLOAD and cmd == "ARRIVED_AT_CHECKPOINT_C":
                self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_UNLOAD)
                self.send_stop(truck_id)  # 트럭 정지
                gate_id = payload.get("gate_id", "GATE_B")
                self._open_gate_and_log(gate_id, truck_id)
                return
            
            # -------------------------------------------------------------------

            # 게이트 B 열림 확인
            elif state == TruckState.WAIT_GATE_OPEN_FOR_UNLOAD and cmd == "ACK_GATE_OPENED":
                self.set_state(truck_id, TruckState.MOVE_TO_UNLOAD)
                self.send_run(truck_id)
                return
            
            # -------------------------------------------------------------------

            # CHECKPOINT_D 도착 (GATE_B 닫기)
            elif state == TruckState.MOVE_TO_UNLOAD and cmd == "ARRIVED_AT_CHECKPOINT_D":
                # self.send_stop(truck_id)  # 트럭 정지
                gate_id = payload.get("gate_id", "GATE_B")
                self._close_gate_and_log(gate_id, truck_id)
                return
            
            # -------------------------------------------------------------------

            # 벨트 도착
            elif state == TruckState.MOVE_TO_UNLOAD and cmd == "ARRIVED_AT_BELT":
                self.set_state(truck_id, TruckState.WAIT_UNLOAD)
                self.send_stop(truck_id)  # 트럭 정지
                return

            # -------------------------------------------------------------------

            # 하차 시작
            elif state == TruckState.WAIT_UNLOAD and cmd == "START_UNLOADING":
                self.set_state(truck_id, TruckState.UNLOADING)
                if self.belt_controller:
                    print(f"[FSM] {truck_id} → 벨트에 BELTACT 명령 전송")
                    if not self.belt_controller.send_command("BELTACT"):
                        print(f"[⚠️ 경고] {truck_id} → 벨트 작동 거부됨 (컨테이너 가득 참)")
                return

            # -------------------------------------------------------------------

            # 하차 완료
            elif state == TruckState.UNLOADING and cmd == "FINISH_UNLOADING":
                self.set_state(truck_id, TruckState.MOVE_TO_STANDBY)
                self.send_run(truck_id)

                mission = self.mission_manager.get_mission_by_truck(truck_id)
                if mission:
                    mission.update_status("COMPLETED")
                    print(f"[✅ 미션 완료] {mission.mission_id} 완료 처리됨")

                    status_code = mission.status.name if isinstance(mission.status, MissionStatus) else str(mission.status)
                    status_label = mission.status.value if isinstance(mission.status, MissionStatus) else str(mission.status)

                    self.mission_manager.db.update_mission_completion(
                        mission_id=mission.mission_id,
                        status_code=status_code,
                        status_label=status_label,
                        timestamp_completed=mission.timestamp_completed
                    )
                return

            # -------------------------------------------------------------------

            # 비상 상황
            elif cmd == "EMERGENCY_TRIGGERED":
                self.set_state(truck_id, TruckState.EMERGENCY_STOP)
                self.send_stop(truck_id)  # 트럭 정지
                if self.belt_controller:
                    print(f"[FSM] {truck_id} → 벨트에 EMRSTOP 명령 전송")
                    self.belt_controller.send_command("EMRSTOP")
                return

            # -------------------------------------------------------------------

            # 비상 상황 해제
            elif state == TruckState.EMERGENCY_STOP and cmd == "RESET":
                self.set_state(truck_id, TruckState.IDLE)
                return
        
            # -------------------------------------------------------------------

            # 상태 초기화
            elif cmd == "RESET":
                print(f"[🔁 RESET] {truck_id} 상태를 IDLE로 초기화")
                self.set_state(truck_id, TruckState.IDLE)
                return

            print(f"[FSM] 상태 전이 없음: 상태={state.name}, 트리거={cmd}")
        except Exception as e:
            print(f"[FSM] 오류 발생: {e}")

    def check_battery(self, truck_id: str) -> bool:
        """배터리 상태 확인"""
        battery = self.battery_manager.get_battery(truck_id)
        print(f"[🔋 배터리 체크] {truck_id}의 배터리: {battery.level}%")
        return battery.level > 30  # 30% 이상이면 True