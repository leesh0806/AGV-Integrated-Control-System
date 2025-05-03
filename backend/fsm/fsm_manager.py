# backend/fsm/fsm_manager.py

from fsm.state_enum import TruckState
from tcpio.truck_commander import TruckCommandSender

class TruckFSMManager:
    def __init__(self, gate_controller, mission_manager):
        self.gate_controller = gate_controller
        self.mission_manager = mission_manager
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

    def handle_trigger(self, truck_id, cmd, payload):
        state = self.get_state(truck_id)
        print(f"[FSM] 트리거: {truck_id}, 상태={state.name}, 트리거={cmd}")

        # 1. 미션 할당
        if state == TruckState.IDLE and cmd == "ASSIGN_MISSION":
            mission = self.mission_manager.assign_next_to_truck(truck_id)
            if mission:
                self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_LOAD)
                print(f"[지시] {truck_id} → CHECKPOINT_A로 이동")
                self.send_run(truck_id)

                # ✅ 여기 추가: MISSION_ASSIGNED 응답 보내기
                if self.command_sender:
                    self.command_sender.send(
                        truck_id,
                        "MISSION_ASSIGNED",
                        {"mission_id": mission.mission_id, "source": mission.source}
                    )
                    print(f"[📤 MISSION_ASSIGNED 전송] → {truck_id}, source={mission.source}")

            else:
                print(f"[⚠️ 미션 없음] {truck_id}에게 할당할 미션이 없습니다.")
            return

        # 2. CHECKPOINT_A 도착 → 게이트 열기
        elif state == TruckState.MOVE_TO_GATE_FOR_LOAD and cmd == "ARRIVED_AT_CHECKPOINT_A":
            self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_LOAD)
            gate_id = payload.get("gate_id", "GATE_A")
            self.gate_controller.open_gate(gate_id)
            return

        # 3. 게이트 A 열림 → LOAD로 이동
        elif state == TruckState.WAIT_GATE_OPEN_FOR_LOAD and cmd == "ACK_GATE_OPENED":
            self.set_state(truck_id, TruckState.MOVE_TO_LOAD)
            self.send_run(truck_id)
            return

        # 4. CPB는 무시 (게이트 통과 확인용)
        elif cmd == "ARRIVED_AT_CHECKPOINT_B":
            print(f"[FSM] {truck_id}: CHECKPOINT_B 도착 감지 (상태 유지)")
            return

        # 5. LOAD_A 또는 LOAD_B 도착
        elif state == TruckState.MOVE_TO_LOAD and cmd in ["ARRIVED_AT_LOAD_A", "ARRIVED_AT_LOAD_B"]:
            self.set_state(truck_id, TruckState.WAIT_LOAD)
            return

        # 6. 적재 시작
        elif state == TruckState.WAIT_LOAD and cmd == "START_LOADING":
            self.set_state(truck_id, TruckState.LOADING)
            return

        # 7. 적재 완료 → CHECKPOINT_C로 이동
        elif state == TruckState.LOADING and cmd == "FINISH_LOADING":
            self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_UNLOAD)
            print(f"[지시] {truck_id} → CHECKPOINT_C로 이동")
            self.send_run(truck_id)
            return

        # 8. CHECKPOINT_C 도착 → 게이트 B 열기
        elif state == TruckState.MOVE_TO_GATE_FOR_UNLOAD and cmd == "ARRIVED_AT_CHECKPOINT_C":
            self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_UNLOAD)
            gate_id = payload.get("gate_id", "GATE_B")
            self.gate_controller.open_gate(gate_id)
            return

        # 9. 게이트 B 열림 → 하차장으로 이동
        elif state == TruckState.WAIT_GATE_OPEN_FOR_UNLOAD and cmd == "ACK_GATE_OPENED":
            self.set_state(truck_id, TruckState.MOVE_TO_UNLOAD)
            self.send_run(truck_id)
            return

        # 10. CPD는 무시 (게이트 통과 확인용)
        elif cmd == "ARRIVED_AT_CHECKPOINT_D":
            print(f"[FSM] {truck_id}: CHECKPOINT_D 도착 감지 (상태 유지)")
            return

        # 11. BELT 도착
        elif state == TruckState.MOVE_TO_UNLOAD and cmd == "ARRIVED_AT_BELT":
            self.set_state(truck_id, TruckState.WAIT_UNLOAD)
            return

        # 12. 하차 시작
        elif state == TruckState.WAIT_UNLOAD and cmd == "START_UNLOADING":
            self.set_state(truck_id, TruckState.UNLOADING)
            return

        # 13. 하차 완료 → STANDBY로 이동
        elif state == TruckState.UNLOADING and cmd == "FINISH_UNLOADING":
            self.set_state(truck_id, TruckState.MOVE_TO_STANDBY)
            self.send_run(truck_id)
            return

        # 14. STANDBY 도착
        elif state == TruckState.MOVE_TO_STANDBY and cmd == "ARRIVED_AT_STANDBY":
            self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)
            return

        # 15. 긴급 정지
        elif cmd == "EMERGENCY_TRIGGERED":
            self.set_state(truck_id, TruckState.EMERGENCY_STOP)
            return

        # 16. 복구
        elif state == TruckState.EMERGENCY_STOP and cmd == "RESET":
            self.set_state(truck_id, TruckState.IDLE)
            return

        # 그 외
        print(f"[FSM] 상태 전이 없음: 상태={state.name}, 트리거={cmd}")
