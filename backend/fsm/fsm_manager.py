from fsm.state_enum import TruckState
from tcpio.truck_commander import TruckCommandSender
from datetime import datetime

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

        elif state == TruckState.MOVE_TO_GATE_FOR_LOAD and cmd == "ARRIVED_AT_CHECKPOINT_A":
            self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_LOAD)
            gate_id = payload.get("gate_id", "GATE_A")
            self.gate_controller.open_gate(gate_id)
            return

        elif state == TruckState.WAIT_GATE_OPEN_FOR_LOAD and cmd == "ACK_GATE_OPENED":
            self.set_state(truck_id, TruckState.MOVE_TO_LOAD)
            self.send_run(truck_id)
            return

        elif cmd == "ARRIVED_AT_CHECKPOINT_B":
            print(f"[FSM] {truck_id}: CHECKPOINT_B 도착 감지 (상태 유지)")
            return

        elif state == TruckState.MOVE_TO_LOAD and cmd in ["ARRIVED_AT_LOAD_A", "ARRIVED_AT_LOAD_B"]:
            self.set_state(truck_id, TruckState.WAIT_LOAD)
            return

        elif state == TruckState.WAIT_LOAD and cmd == "START_LOADING":
            self.set_state(truck_id, TruckState.LOADING)
            return

        elif state == TruckState.LOADING and cmd == "FINISH_LOADING":
            self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_UNLOAD)
            print(f"[지시] {truck_id} → CHECKPOINT_C로 이동")
            self.send_run(truck_id)
            return

        elif state == TruckState.MOVE_TO_GATE_FOR_UNLOAD and cmd == "ARRIVED_AT_CHECKPOINT_C":
            self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_UNLOAD)
            gate_id = payload.get("gate_id", "GATE_B")
            self.gate_controller.open_gate(gate_id)
            return

        elif state == TruckState.WAIT_GATE_OPEN_FOR_UNLOAD and cmd == "ACK_GATE_OPENED":
            self.set_state(truck_id, TruckState.MOVE_TO_UNLOAD)
            self.send_run(truck_id)
            return

        elif cmd == "ARRIVED_AT_CHECKPOINT_D":
            print(f"[FSM] {truck_id}: CHECKPOINT_D 도착 감지 (상태 유지)")
            return

        elif state == TruckState.MOVE_TO_UNLOAD and cmd == "ARRIVED_AT_BELT":
            self.set_state(truck_id, TruckState.WAIT_UNLOAD)
            return

        elif state == TruckState.WAIT_UNLOAD and cmd == "START_UNLOADING":
            self.set_state(truck_id, TruckState.UNLOADING)
            return

        elif state == TruckState.UNLOADING and cmd == "FINISH_UNLOADING":
            self.set_state(truck_id, TruckState.MOVE_TO_STANDBY)
            self.send_run(truck_id)

            # ✅ 미션 완료 처리
            mission = self.mission_manager.get_mission_by_truck(truck_id)
            if mission:
                mission.status_code = "COMPLETED"
                mission.status_label = "완료됨"
                mission.timestamp_completed = datetime.now()
                print(f"[✅ 미션 완료] {mission.mission_id} 완료 처리됨")

                # 방법 1
                # self.mission_manager.save_to_db()

                # 방법 2
                self.mission_manager.db.update_mission_completion(
                    mission_id=mission.mission_id,
                    status_code=mission.status_code,
                    status_label=mission.status_label,
                    timestamp_completed=mission.timestamp_completed
                )
            return

        elif state == TruckState.MOVE_TO_STANDBY and cmd == "ARRIVED_AT_STANDBY":
            self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)
            return

        elif cmd == "EMERGENCY_TRIGGERED":
            self.set_state(truck_id, TruckState.EMERGENCY_STOP)
            return

        elif state == TruckState.EMERGENCY_STOP and cmd == "RESET":
            self.set_state(truck_id, TruckState.IDLE)
            return

        elif cmd == "RESET":
            print(f"[🔁 RESET] {truck_id} 상태를 IDLE로 초기화")
            self.set_state(truck_id, TruckState.IDLE)
            return

        print(f"[FSM] 상태 전이 없음: 상태={state.name}, 트리거={cmd}")
