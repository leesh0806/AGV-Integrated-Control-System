# backend/fsm/fsm_manager.py

from .state_enum import TruckState
from ..mission.status import MissionStatus
from ..tcpio.truck_commander import TruckCommandSender
from datetime import datetime

class TruckFSMManager:
    def __init__(self, gate_controller, mission_manager, belt_controller=None):
        self.gate_controller = gate_controller
        self.mission_manager = mission_manager
        self.belt_controller = belt_controller
        self.states = {}
        self.command_sender = None

    def set_commander(self, commander: TruckCommandSender):
        self.command_sender = commander

    def get_state(self, truck_id):
        return self.states.get(truck_id, TruckState.IDLE)

    def set_state(self, truck_id, new_state):
        prev = self.get_state(truck_id)
        self.states[truck_id] = new_state
        print(f"[FSM] {truck_id}: {prev.name} → {new_state.name}")

    def send_run(self, truck_id):
        if self.command_sender:
            self.command_sender.send(truck_id, "RUN")

    def _open_gate_and_log(self, gate_id: str, truck_id: str):
        success = self.gate_controller.open_gate(gate_id)
        if success:
            print(f"[🔓 GATE OPEN] {gate_id} ← by {truck_id}")
            if self.command_sender:
                self.command_sender.send(truck_id, "GATE_OPENED", {"gate_id": gate_id})
        return success

    def _close_gate_and_log(self, gate_id: str, truck_id: str):
        success = self.gate_controller.close_gate(gate_id)
        if success:
            print(f"[🔒 GATE CLOSE] {gate_id} ← by {truck_id}")
            if self.command_sender:
                self.command_sender.send(truck_id, "GATE_CLOSED", {"gate_id": gate_id})
        return success

    def handle_trigger(self, truck_id, cmd, payload):
        state = self.get_state(truck_id)
        print(f"[FSM] 트리거: {truck_id}, 상태={state.name}, 트리거={cmd}")

        # IDLE 상태에서 미션 할당
        if state == TruckState.IDLE and cmd == "ASSIGN_MISSION":
            print("[DEBUG] ASSIGN_MISSION: DB에서 미션 새로 불러옴")
            self.mission_manager.load_from_db()
            mission = self.mission_manager.assign_next_to_truck(truck_id)
            if mission:
                self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_LOAD)
                print(f"[지시] {truck_id} → CHECKPOINT_A로 이동")
                self.send_run(truck_id)
                self.command_sender.send(truck_id, "MISSION_ASSIGNED", {
                    "mission_id": mission.mission_id,
                    "source": mission.source
                })
            else:
                # 미션이 없을 때도 트럭에게 NO_MISSION 메시지 전송
                if self.command_sender:
                    self.command_sender.send(truck_id, "NO_MISSION", {})
            return

        # 게이트 A에 도착
        elif state == TruckState.MOVE_TO_GATE_FOR_LOAD and cmd == "ARRIVED_AT_CHECKPOINT_A":
            self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_LOAD)
            gate_id = payload.get("gate_id", "GATE_A")
            self._open_gate_and_log(gate_id, truck_id)
            return

        # 게이트 열림 확인
        elif state == TruckState.WAIT_GATE_OPEN_FOR_LOAD and cmd == "ACK_GATE_OPENED":
            self.set_state(truck_id, TruckState.MOVE_TO_LOAD)
            self.send_run(truck_id)
            return

        # CHECKPOINT_B 도착 (GATE_A 닫기)
        elif state == TruckState.MOVE_TO_LOAD and cmd == "ARRIVED_AT_CHECKPOINT_B":
            gate_id = payload.get("gate_id", "GATE_A")
            self._close_gate_and_log(gate_id, truck_id)
            return

        # 적재장 도착
        elif state == TruckState.MOVE_TO_LOAD and (cmd == "ARRIVED_AT_LOAD_A" or cmd == "ARRIVED_AT_LOAD_B"):
            self.set_state(truck_id, TruckState.WAIT_LOAD)
            return

        # 적재 시작
        elif state == TruckState.WAIT_LOAD and cmd == "START_LOADING":
            self.set_state(truck_id, TruckState.LOADING)
            return

        # 적재 완료
        elif state == TruckState.LOADING and cmd == "FINISH_LOADING":
            self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_UNLOAD)
            print(f"[지시] {truck_id} → CHECKPOINT_C로 이동")
            self.send_run(truck_id)
            return

        # 게이트 B에 도착
        elif state == TruckState.MOVE_TO_GATE_FOR_UNLOAD and cmd == "ARRIVED_AT_CHECKPOINT_C":
            self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_UNLOAD)
            gate_id = payload.get("gate_id", "GATE_B")
            self._open_gate_and_log(gate_id, truck_id)
            return

        # 게이트 B 열림 확인
        elif state == TruckState.WAIT_GATE_OPEN_FOR_UNLOAD and cmd == "ACK_GATE_OPENED":
            self.set_state(truck_id, TruckState.MOVE_TO_UNLOAD)
            self.send_run(truck_id)
            return

        # CHECKPOINT_D 도착 (GATE_B 닫기)
        elif state == TruckState.MOVE_TO_UNLOAD and cmd == "ARRIVED_AT_CHECKPOINT_D":
            gate_id = payload.get("gate_id", "GATE_B")
            self._close_gate_and_log(gate_id, truck_id)
            return

        # 벨트 도착
        elif state == TruckState.MOVE_TO_UNLOAD and cmd == "ARRIVED_AT_BELT":
            self.set_state(truck_id, TruckState.WAIT_UNLOAD)
            return

        # 하차 시작
        elif state == TruckState.WAIT_UNLOAD and cmd == "START_UNLOADING":
            self.set_state(truck_id, TruckState.UNLOADING)
            if self.belt_controller:
                print(f"[FSM] {truck_id} → 벨트에 BELTACT 명령 전송")
                if not self.belt_controller.send_command("BELTACT"):
                    print(f"[⚠️ 경고] {truck_id} → 벨트 작동 거부됨 (컨테이너 가득 참)")
            return

        # 하차 완료
        elif state == TruckState.UNLOADING and cmd == "FINISH_UNLOADING":
            self.set_state(truck_id, TruckState.MOVE_TO_STANDBY)
            self.send_run(truck_id)

            mission = self.mission_manager.get_mission_by_truck(truck_id)
            if mission:
                mission.update_status("COMPLETED")
                print(f"[✅ 미션 완료] {mission.mission_id} 완료 처리됨")

                # ✅ status Enum 안전 처리
                status_code = mission.status.name if isinstance(mission.status, MissionStatus) else str(mission.status)
                status_label = mission.status.value if isinstance(mission.status, MissionStatus) else str(mission.status)

                self.mission_manager.db.update_mission_completion(
                    mission_id=mission.mission_id,
                    status_code=status_code,
                    status_label=status_label,
                    timestamp_completed=mission.timestamp_completed
                )
            return

        # 대기장 도착
        elif state == TruckState.MOVE_TO_STANDBY and cmd == "ARRIVED_AT_STANDBY":
            self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)
            # ★ 미션 자동 재할당 트리거
            self.handle_trigger(truck_id, "ASSIGN_MISSION", {})
            return

        # 비상 상황
        elif cmd == "EMERGENCY_TRIGGERED":
            self.set_state(truck_id, TruckState.EMERGENCY_STOP)
            if self.belt_controller:
                print(f"[FSM] {truck_id} → 벨트에 EMRSTOP 명령 전송")
                self.belt_controller.send_command("EMRSTOP")
            return

        # 비상 상황 해제
        elif state == TruckState.EMERGENCY_STOP and cmd == "RESET":
            self.set_state(truck_id, TruckState.IDLE)
            return

        # 상태 초기화
        elif cmd == "RESET":
            print(f"[🔁 RESET] {truck_id} 상태를 IDLE로 초기화")
            self.set_state(truck_id, TruckState.IDLE)
            return

        print(f"[FSM] 상태 전이 없음: 상태={state.name}, 트리거={cmd}")
