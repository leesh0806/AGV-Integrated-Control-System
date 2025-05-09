# backend/controller/app_controller.py

from backend.serialio.port_manager import SerialManager
from backend.serialio.belt_controller import BeltController
from backend.serialio.gate_controller import GateController

from backend.mission.db import MissionDB
from backend.mission.mission_controller import MissionManager

from backend.tcpio.truck_commander import TruckCommandSender
from backend.api.api import set_truck_position

from backend.truck_status.truck_state_manager import TruckStatusManager
from backend.truck_status.db import TruckStatusDB

from backend.fsm.state_enum import TruckState
from backend.fsm.state_machine import TruckFSMManager
from backend.fsm.truck_message_handler import MessageHandler


class AppController:
    def __init__(self, port_map, use_fake=False):
        # Serial 연결
        self.serial_manager = SerialManager(port_map, use_fake=use_fake)

        # Mission DB 초기화
        self.db = MissionDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        self.mission_manager = MissionManager(self.db)

        # TruckStatusDB 초기화
        self.status_db = TruckStatusDB(
            host="localhost",
            user="root",
            password="jinhyuk2dacibul",
            database="dust"
        )
        self.status_manager = TruckStatusManager(self.status_db)

        # 장치 컨트롤러들
        self.belt_controller = BeltController(self.serial_manager.controllers["BELT"])
        self.gate_controller = GateController(self.serial_manager)
        
        # FSM 관리자
        self.fsm_manager = TruckFSMManager(
            gate_controller=self.gate_controller,
            mission_manager=self.mission_manager,
            belt_controller=self.belt_controller,
            status_manager=self.status_manager
        )

        # 트럭 메시지 핸들러
        self.truck_manager = MessageHandler(self.fsm_manager)
        self.truck_manager.set_status_manager(self.status_manager)

        # 초기 TruckCommandSender 설정
        self.set_truck_commander({})

        self.truck_positions = {}

    # 트럭 명령 전송자 설정
    def set_truck_commander(self, truck_socket_map: dict):
        commander = TruckCommandSender(truck_socket_map)
        self.fsm_manager.set_commander(commander)

    # 메시지 처리
    def handle_message(self, msg: dict):
        sender = msg.get("sender")
        cmd = msg.get("cmd", "").strip().upper()

        print(f"[📨 AppController] sender={sender}, cmd={cmd}")

        # 1. 벨트 디버깅/수동 제어 명령
        if self._is_manual_belt_command(cmd):
            self._handle_manual_belt_command(cmd)
            return

        # 2. 게이트 수동 제어 명령 (예: "GATE_A_OPEN")
        if cmd.startswith("GATE_"):
            self._handle_manual_gate_command(cmd)
            return

        # 트럭 위치 ARRIVED 명령 처리
        if cmd == "ARRIVED":
            position = msg.get("payload", {}).get("position")
            if sender and position:
                self.truck_positions[sender] = position.upper()
                set_truck_position(sender, position.upper())  # Flask API와 동기화
            # ★ 반드시 트럭 FSM에도 메시지 전달
            self.truck_manager.handle_message(msg)
            return

        # 3. 트럭 FSM 관련 명령
        self.truck_manager.handle_message(msg)

    # ─────────────────────────────────────────────

    # 수동 벨트 제어 명령 확인
    def _is_manual_belt_command(self, cmd: str) -> bool:
        return cmd in {"BELTACT", "BELTOFF", "EMRSTOP", "A_FULL"}

    # 수동 벨트 제어 명령 처리
    def _handle_manual_belt_command(self, cmd: str):
        print(f"[⚙️ 수동 벨트 제어] CMD: {cmd}")
        self.belt_controller.handle_message(cmd)

    # 수동 게이트 제어 명령 처리
    def _handle_manual_gate_command(self, cmd: str):
        parts = cmd.split("_")
        if len(parts) == 3:
            gate_id = f"GATE_{parts[1]}"
            action = parts[2]
            if action == "OPEN":
                self.gate_controller.open_gate(gate_id)
            elif action == "CLOSE":
                self.gate_controller.close_gate(gate_id)
        else:
            print(f"[❌ 게이트 명령 포맷 오류] {cmd}")

    def handle_command(self, truck_id, cmd, payload):
        try:
            # 미션 관련 명령 처리
            if cmd == "ASSIGN_MISSION":
                self.fsm_manager.handle_trigger(truck_id, cmd, payload)
                return
            
            # 미션 완료 처리
            elif cmd == "FINISH_UNLOADING":
                self.fsm_manager.handle_trigger(truck_id, cmd, payload)
                return
            
            # 미션 취소 처리
            elif cmd == "CANCEL_MISSION":
                missions = self.mission_manager.get_missions_by_truck(truck_id)
                if missions:
                    mission = missions[0]  # 첫 번째 미션 사용
                    self.mission_manager.cancel_mission(mission.mission_id)
                    self.fsm_manager.set_state(truck_id, TruckState.IDLE)
                return
            
            # 기타 명령은 FSM으로 전달
            self.fsm_manager.handle_trigger(truck_id, cmd, payload)
            
        except Exception as e:
            print(f"[컨트롤러] 오류 발생: {e}")
