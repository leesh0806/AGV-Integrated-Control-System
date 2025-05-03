# backend/fsm/fsm_manager.py

from fsm.state_enum import TruckState
from tcpio.truck_commander import TruckCommandSender

class TruckFSMManager:
    def __init__(self, gate_controller, mission_manager):
        self.gate_controller = gate_controller
        self.mission_manager = mission_manager
        self.states = {}  # truck_id → TruckState
        self.command_sender = None

    def set_commander(self, commander: TruckCommandSender):
        self.command_sender = commander

    def get_state(self, truck_id):
        return self.states.get(truck_id, TruckState.IDLE)

    def set_state(self, truck_id, new_state):
        prev = self.get_state(truck_id)
        self.states[truck_id] = new_state
        print(f"[FSM] {truck_id}: {prev.name} → {new_state.name}")

    def handle_trigger(self, truck_id, cmd, payload):
        state = self.get_state(truck_id)
        print(f"[FSM] 트리거: {truck_id}, 상태={state.name}, 트리거={cmd}")

        if state == TruckState.IDLE and cmd == "ASSIGN_MISSION":
            self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_LOAD)
            print(f"[지시] {truck_id} → 게이트로 이동")

        elif state == TruckState.MOVE_TO_GATE_FOR_LOAD and cmd.startswith("ARRIVED_AT"):
            self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_LOAD)
            gate_id = payload.get("gate_id", "GATE_A")
            self.gate_controller.open_gate(gate_id)

        elif state == TruckState.WAIT_GATE_OPEN_FOR_LOAD and cmd == "ACK_GATE_OPENED":
            self.set_state(truck_id, TruckState.MOVE_TO_LOAD)

        elif state == TruckState.MOVE_TO_LOAD and cmd.startswith("ARRIVED_AT"):
            self.set_state(truck_id, TruckState.WAIT_LOAD)

        elif state == TruckState.WAIT_LOAD and cmd == "START_LOADING":
            self.set_state(truck_id, TruckState.LOADING)

        elif state == TruckState.LOADING and cmd == "FINISH_LOADING":
            self.set_state(truck_id, TruckState.MOVE_TO_GATE_FOR_UNLOAD)

        elif state == TruckState.MOVE_TO_GATE_FOR_UNLOAD and cmd.startswith("ARRIVED_AT"):
            self.set_state(truck_id, TruckState.WAIT_GATE_OPEN_FOR_UNLOAD)
            gate_id = payload.get("gate_id", "GATE_B")
            self.gate_controller.open_gate(gate_id)

        elif state == TruckState.WAIT_GATE_OPEN_FOR_UNLOAD and cmd == "ACK_GATE_OPENED":
            self.set_state(truck_id, TruckState.MOVE_TO_UNLOAD)

        elif state == TruckState.MOVE_TO_UNLOAD and cmd.startswith("ARRIVED_AT"):
            self.set_state(truck_id, TruckState.WAIT_UNLOAD)

        elif state == TruckState.WAIT_UNLOAD and cmd == "START_UNLOADING":
            self.set_state(truck_id, TruckState.UNLOADING)

        elif state == TruckState.UNLOADING and cmd == "FINISH_UNLOADING":
            self.set_state(truck_id, TruckState.MOVE_TO_STANDBY)

        elif state == TruckState.MOVE_TO_STANDBY and cmd.startswith("ARRIVED_AT"):
            self.set_state(truck_id, TruckState.WAIT_NEXT_MISSION)

        elif cmd == "EMERGENCY_TRIGGERED":
            self.set_state(truck_id, TruckState.EMERGENCY_STOP)

        elif state == TruckState.EMERGENCY_STOP and cmd == "RESET":
            self.set_state(truck_id, TruckState.IDLE)

        else:
            print(f"[FSM] 상태 전이 없음: 상태={state.name}, 트리거={cmd}")

